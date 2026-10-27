"""Yapay zekâ uçları (FR-501…FR-507, TR-006): kayıt açmadan tahmin ve değerlendirme."""

from decimal import Decimal
from typing import Any

from avatar_ml import predict
from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Db, ProductionUser, WebUser
from app.errors import InvalidInput, NotFound
from app.models import AiForecast, Cutting, CuttingOutput, CuttingRecipe, Product, ProductionOrder
from app.models.enums import CuttingStatus, ForecastTarget, ProductionStatus
from app.models.types import utcnow
from app.services.ai import PlannedLot, predict_cutting, predict_production
from app.services.cutting import recipe_lines
from app.services.lookups import get_or_404, lot_by_no
from app.services.production import order_summary

router = APIRouter(prefix="/ai", tags=["yapay zekâ"])


class PlannedLotIn(BaseModel):
    lot_no: str
    qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class ProductionForecastIn(BaseModel):
    subcontractor_id: int
    output_product_id: int
    service_unit_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=4)
    inputs: list[PlannedLotIn] = Field(min_length=1)


class ProductionForecastOut(BaseModel):
    model_version: str
    expected_qty: Decimal
    expected_output_kg: Decimal
    yield_main_pct: Decimal
    raw_material_cost: Decimal
    service_amount: Decimal
    ekp: Decimal
    baseline_qty: Decimal
    baseline_yield_pct: Decimal
    baseline_ekp: Decimal


class CuttingForecastIn(BaseModel):
    recipe_id: int
    input_lot_no: str
    input_qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class CuttingForecastLineOut(BaseModel):
    key: str
    name: str
    standard_kg: Decimal  # referans: reçete oranı × giriş
    predicted_kg: Decimal
    share_pct: Decimal


class CuttingForecastOut(BaseModel):
    model_version: str
    lines: list[CuttingForecastLineOut]


class RealComparisonOut(BaseModel):
    model: str
    document_no: str
    item: str
    predicted: Decimal
    actual: Decimal
    deviation: Decimal
    unit: str


class EvaluationOut(BaseModel):
    available: bool
    message: str | None
    metadata: dict[str, Any] | None
    real: list[RealComparisonOut]


@router.post("/production-forecast", response_model=ProductionForecastOut)
def production_forecast(body: ProductionForecastIn, db: Db, _: ProductionUser) -> ProductionForecastOut:
    """Model A: kayıt açmadan beklenen paket sayısı ve EKP (emir formunda ön izleme)."""
    product = get_or_404(db, Product, body.output_product_id, "Mamul")
    planned = [PlannedLot(lot_by_no(db, i.lot_no), i.qty) for i in body.inputs]
    try:
        result = predict_production(
            db,
            subcontractor_id=body.subcontractor_id,
            product=product,
            planned=planned,
            service_unit_price=body.service_unit_price,
        )
    except predict.ModelUnavailable as error:
        raise NotFound(f"Model A kullanılamıyor: {error}") from error
    except ValueError as error:
        raise InvalidInput(str(error)) from error
    data = vars(result).copy()
    data.pop("features")
    return ProductionForecastOut(**data)


@router.post("/cutting-forecast", response_model=CuttingForecastOut)
def cutting_forecast(body: CuttingForecastIn, db: Db, _: ProductionUser) -> CuttingForecastOut:
    """Model B: kayıt açmadan parça bazında beklenen kg; referans (standart oran) ile yan yana."""
    recipe = get_or_404(db, CuttingRecipe, body.recipe_id, "Reçete")
    lot = lot_by_no(db, body.input_lot_no)
    try:
        result = predict_cutting(
            db, species=recipe.species, input_lot=lot, input_qty=body.input_qty, at=utcnow()
        )
    except predict.ModelUnavailable as error:
        raise NotFound(f"Model B kullanılamıyor: {error}") from error
    predicted = {line.key: line for line in result.lines}
    lines = []
    for line in recipe_lines(db, recipe.id):
        product = db.get(Product, line.product_id) if line.product_id else None
        key = product.code if product else "FIRE"
        if key not in predicted:
            continue
        lines.append(
            CuttingForecastLineOut(
                key=key,
                name=product.name if product else "Fire",
                standard_kg=(line.standard_ratio * body.input_qty).quantize(Decimal("0.001")),
                predicted_kg=predicted[key].predicted_kg,
                share_pct=predicted[key].share_pct,
            )
        )
    return CuttingForecastOut(model_version=result.model_version, lines=lines)


@router.get("/evaluation", response_model=EvaluationOut)
def evaluation(db: Db, _: WebUser) -> EvaluationOut:
    """Model sürümleri, veri özeti, referans ve model hataları; sistemdeki gerçek kayıtlarla karşılaştırma."""
    try:
        metadata = predict.metadata()
    except predict.ModelUnavailable as error:
        return EvaluationOut(available=False, message=str(error), metadata=None, real=_real(db))
    return EvaluationOut(available=True, message=None, metadata=metadata, real=_real(db))


def _real(db: Db) -> list[RealComparisonOut]:
    """Sistemde tahmini kaydedilmiş ve sonucu belli olmuş emir ve parçalamalar."""
    rows: list[RealComparisonOut] = []
    forecasts = db.scalars(select(AiForecast).order_by(AiForecast.id)).all()
    seen: set[tuple[str, int]] = set()
    for record in forecasts:
        if (record.target_type, record.target_id) in seen:
            continue
        seen.add((record.target_type, record.target_id))
        if record.target_type == ForecastTarget.URETIM_EMRI:
            order = db.get(ProductionOrder, record.target_id)
            if order is None or order.status != ProductionStatus.TAMAMLANDI or order.received_qty is None:
                continue
            expected = Decimal(record.prediction["expected_qty"])
            rows.append(
                RealComparisonOut(
                    model="A",
                    document_no=order.order_no,
                    item="Paket sayısı",
                    predicted=expected,
                    actual=order.received_qty,
                    deviation=order.received_qty - expected,
                    unit="adet",
                )
            )
            summary = order_summary(db, order)
            if summary.cost is not None:
                predicted_ekp = Decimal(record.prediction["ekp"]).quantize(Decimal("0.01"))
                rows.append(
                    RealComparisonOut(
                        model="A",
                        document_no=order.order_no,
                        item="EKP",
                        predicted=predicted_ekp,
                        actual=summary.cost.ekp_display,
                        deviation=summary.cost.ekp_display - predicted_ekp,
                        unit="€",
                    )
                )
        else:
            cutting = db.get(Cutting, record.target_id)
            if cutting is None or cutting.status != CuttingStatus.ONAYLANDI:
                continue
            outputs = db.scalars(select(CuttingOutput).where(CuttingOutput.cutting_id == cutting.id)).all()
            for output in outputs:
                if output.predicted_qty is None or output.actual_qty is None:
                    continue
                product = db.get(Product, output.product_id) if output.product_id else None
                rows.append(
                    RealComparisonOut(
                        model="B",
                        document_no=cutting.cutting_no,
                        item=product.name if product else "Fire",
                        predicted=output.predicted_qty,
                        actual=output.actual_qty,
                        deviation=output.actual_qty - output.predicted_qty,
                        unit="kg",
                    )
                )
    return rows
