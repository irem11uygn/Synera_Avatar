"""Yapay zekâ tahminleri: iş anında hesaplanır ve kaydedilir (FR-501…FR-504, TR-006; ADR-005).

- Model A: dış üretim emri açılırken et bazlı verim → beklenen paket sayısı ve EKP. EKP'nin
  hammadde kısmı tahmin değildir: planlanan lotların bugünkü değeridir; tahmin edilen yalnız
  paket sayısıdır (dolayısıyla birim maliyetin paydası ve hizmet tutarı).
- Model B: parçalama taslağı açılırken parça payları → her satır için beklenen kg
  (cutting_outputs.predicted_qty).

Tahmin kaydı sonradan değişmez; "tahmin – gerçek – sapma" bu kayda göre hesaplanır.
Model dosyası yoksa ya da tahmin hata verirse iş akışı durmaz: None döner, günlüğe yazılır
(architecture.md §6). İzleme ve geri çağırma hiçbir yerde tahmin kullanmaz (CON-003).
"""

import logging
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal

from avatar_ml import predict
from avatar_ml.features import CuttingFeatures, ProductionFeatures
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.money import round_money, round_percent, round_qty, round_unit_cost
from app.models import (
    AiForecast,
    Cutting,
    CuttingOutput,
    Lot,
    Partner,
    Product,
    ProductionInput,
    ProductionOrder,
    Purchase,
    PurchaseLine,
)
from app.models.enums import AiModel, BaseUnit, ForecastTarget, RecipeLineType
from app.models.types import utcnow

logger = logging.getLogger(__name__)

SPICE_CODES = {"BAHARAT"}
CASING_CODES = {"BAGIRSAK"}
FIRE_KEY = "FIRE"


@dataclass(frozen=True)
class PlannedLot:
    lot: Lot
    qty: Decimal


@dataclass(frozen=True)
class ProductionForecast:
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
    features: ProductionFeatures


@dataclass(frozen=True)
class CuttingForecastLine:
    key: str  # ürün kodu ya da FIRE
    share_pct: Decimal
    predicted_kg: Decimal


@dataclass(frozen=True)
class CuttingForecast:
    model_version: str
    lines: list[CuttingForecastLine]
    features: CuttingFeatures


# --- Model A ---


def _lot_date(session: Session, lot: Lot) -> date:
    if lot.produced_at:
        return lot.produced_at
    purchased = session.scalar(
        select(Purchase.doc_date)
        .join(PurchaseLine, PurchaseLine.purchase_id == Purchase.id)
        .where(PurchaseLine.lot_id == lot.id)
    )
    return purchased or lot.created_at.date()


def _code(session: Session, partner_id: int | None) -> str:
    partner = session.get(Partner, partner_id) if partner_id else None
    return partner.code if partner else "BILINMIYOR"


def production_features(
    session: Session, *, subcontractor_id: int, planned: list[PlannedLot], at: datetime
) -> ProductionFeatures:
    products = {p.lot.id: session.get(Product, p.lot.product_id) for p in planned}
    kg_lots = [p for p in planned if products[p.lot.id] and products[p.lot.id].base_unit == BaseUnit.KG]
    if not kg_lots:
        raise ValueError("Emirde kg ile izlenen hammadde yok; et bazlı verim tahmin edilemez.")
    main = max(kg_lots, key=lambda p: p.qty)

    def total(codes: set[str]) -> float:
        return float(sum((p.qty for p in planned if products[p.lot.id].code in codes), Decimal(0)))

    return ProductionFeatures(
        subcontractor=_code(session, subcontractor_id),
        meat_supplier=_code(session, main.lot.supplier_id),
        meat_kg=float(main.qty),
        spice_kg=total(SPICE_CODES),
        casing_kg=total(CASING_CODES),
        meat_age_days=max(0, (at.date() - _lot_date(session, main.lot)).days),
        month=at.month,
    )


def _packages(product: Product, output_kg: float) -> Decimal:
    if product.base_unit == BaseUnit.ADET:
        return Decimal(max(1, math.floor(output_kg / float(product.unit_weight_kg or 1))))
    return round_qty(Decimal(str(output_kg)))


def predict_production(
    session: Session,
    *,
    subcontractor_id: int,
    product: Product,
    planned: list[PlannedLot],
    service_unit_price: Decimal | None,
    at: datetime | None = None,
) -> ProductionForecast:
    """Kayıt açmadan Model A tahmini (hata yükseltebilir; çağıran yakalar)."""
    features = production_features(
        session, subcontractor_id=subcontractor_id, planned=planned, at=at or utcnow()
    )
    model_yield, baseline_yield, version = predict.production_yield(features)
    raw = round_money(
        sum(
            (
                p.lot.remaining_value * p.qty / p.lot.remaining_qty
                if p.lot.remaining_qty
                else p.lot.unit_cost * p.qty
                for p in planned
            ),
            Decimal(0),
        )
    )
    price = service_unit_price or Decimal(0)

    def plan(yield_: float) -> tuple[Decimal, Decimal, Decimal]:
        qty = _packages(product, features.meat_kg * yield_)
        service = round_money(price * qty)
        return qty, service, round_unit_cost((raw + service) / qty)

    qty, service, ekp = plan(model_yield)
    baseline_qty, _, baseline_ekp = plan(baseline_yield)
    return ProductionForecast(
        model_version=version,
        expected_qty=qty,
        expected_output_kg=round_qty(Decimal(str(features.meat_kg * model_yield))),
        yield_main_pct=round_percent(Decimal(str(model_yield * 100))),
        raw_material_cost=raw,
        service_amount=service,
        ekp=ekp,
        baseline_qty=baseline_qty,
        baseline_yield_pct=round_percent(Decimal(str(baseline_yield * 100))),
        baseline_ekp=baseline_ekp,
        features=features,
    )


def forecast_production(session: Session, order: ProductionOrder) -> AiForecast | None:
    """Emir açılırken çağrılır; tahmini kaydeder. Hata iş akışını durdurmaz."""
    try:
        product = session.get(Product, order.output_product_id)
        inputs = session.scalars(select(ProductionInput).where(ProductionInput.order_id == order.id)).all()
        planned = [PlannedLot(session.get(Lot, i.lot_id), i.planned_qty) for i in inputs]  # type: ignore[arg-type]
        assert product is not None and order.subcontractor_id is not None
        result = predict_production(
            session,
            subcontractor_id=order.subcontractor_id,
            product=product,
            planned=planned,
            service_unit_price=order.service_unit_price,
            at=order.ordered_at,
        )
    except SQLAlchemyError:
        raise  # bağlantı/işlem sorunu iş akışının kendi hatasıdır, yutulmaz
    except Exception:
        logger.exception("Model A tahmini yapılamadı (emir %s); iş akışı sürüyor.", order.order_no)
        return None
    record = AiForecast(
        model=AiModel.A_URETIM,
        model_version=result.model_version,
        target_type=ForecastTarget.URETIM_EMRI,
        target_id=order.id,
        features=asdict(result.features),
        prediction={
            "expected_qty": str(result.expected_qty),
            "expected_output_kg": str(result.expected_output_kg),
            "yield_main_pct": str(result.yield_main_pct),
            "raw_material_cost": str(result.raw_material_cost),
            "service_amount": str(result.service_amount),
            "ekp": str(result.ekp),
            "baseline_qty": str(result.baseline_qty),
            "baseline_yield_pct": str(result.baseline_yield_pct),
            "baseline_ekp": str(result.baseline_ekp),
        },
    )
    session.add(record)
    session.flush()
    return record


# --- Model B ---


def _output_key(session: Session, output: CuttingOutput) -> str | None:
    if output.line_type == RecipeLineType.FIRE:
        return FIRE_KEY
    product = session.get(Product, output.product_id) if output.product_id else None
    return product.code if product else None


def predict_cutting(
    session: Session, *, species: str, input_lot: Lot, input_qty: Decimal, at: datetime
) -> CuttingForecast:
    features = CuttingFeatures(
        species=str(species),
        supplier=_code(session, input_lot.supplier_id),
        input_kg=float(input_qty),
        month=at.month,
    )
    shares, version = predict.cutting_shares(features)
    lines = [
        CuttingForecastLine(
            key=key,
            share_pct=round_percent(Decimal(str(share * 100))),
            predicted_kg=round_qty(input_qty * Decimal(str(share))),
        )
        for key, share in shares.items()
    ]
    return CuttingForecast(model_version=version, lines=lines, features=features)


def forecast_cutting(session: Session, cutting: Cutting) -> AiForecast | None:
    """Parçalama taslağı açılırken çağrılır; satırların beklenen kg'ını doldurur ve kaydeder."""
    try:
        lot = session.get(Lot, cutting.input_lot_id)
        assert lot is not None
        result = predict_cutting(
            session, species=cutting.species, input_lot=lot, input_qty=cutting.input_qty, at=cutting.cut_at
        )
    except SQLAlchemyError:
        raise  # bağlantı/işlem sorunu iş akışının kendi hatasıdır, yutulmaz
    except Exception:
        logger.exception("Model B tahmini yapılamadı (parçalama %s); iş akışı sürüyor.", cutting.cutting_no)
        return None
    by_key = {line.key: line.predicted_kg for line in result.lines}
    for output in session.scalars(select(CuttingOutput).where(CuttingOutput.cutting_id == cutting.id)):
        key = _output_key(session, output)
        if key in by_key:
            output.predicted_qty = by_key[key]
    record = AiForecast(
        model=AiModel.B_PARCALAMA,
        model_version=result.model_version,
        target_type=ForecastTarget.PARCALAMA,
        target_id=cutting.id,
        features=asdict(result.features),
        prediction={line.key: str(line.predicted_kg) for line in result.lines},
    )
    session.add(record)
    session.flush()
    return record


def first_forecast(session: Session, target: ForecastTarget, target_id: int) -> AiForecast | None:
    """İş anında kaydedilen ilk tahmin (sonradan değişmez; sapma buna göre hesaplanır)."""
    return session.scalars(
        select(AiForecast)
        .where(AiForecast.target_type == target, AiForecast.target_id == target_id)
        .order_by(AiForecast.id)
    ).first()
