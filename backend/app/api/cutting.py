"""Parçalama — Görev 2 (api.md §2 Parçalama, §4.2): reçeteler ve parçalama işlemleri."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Db, ProductionUser, WebUser
from app.api.fields import UtcDateTime
from app.api.purchases import ExtraCostOut
from app.domain.money import tr_number
from app.models import Cutting, CuttingRecipe, Product
from app.models.enums import AllocationMethod, CuttingStatus, RecipeLineType, Species
from app.services import alarms, audit
from app.services import cutting as service
from app.services.lookups import get_or_404, lot_by_no

router = APIRouter(tags=["parçalama"])

PositiveQty = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]
NonNegativeQty = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=3)]


# --- Reçeteler ---


class RecipeLineIn(BaseModel):
    line_type: RecipeLineType
    product_id: int | None = None
    standard_ratio: Decimal = Field(ge=0, le=1, max_digits=5, decimal_places=4)
    value_per_kg: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=4)
    bears_cost: bool = True


class RecipeIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    input_product_id: int
    species: Species
    default_method: AllocationMethod
    tolerance_kg: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    lines: list[RecipeLineIn] = Field(min_length=1)


class RecipeLineOut(BaseModel):
    id: int
    line_type: RecipeLineType
    product_id: int | None
    product_code: str | None
    product_name: str | None
    standard_ratio: Decimal
    value_per_kg: Decimal | None
    bears_cost: bool
    sort_order: int


class RecipeOut(BaseModel):
    id: int
    code: str
    name: str
    input_product_id: int
    input_product_name: str
    species: Species
    default_method: AllocationMethod
    tolerance_kg: Decimal
    lines: list[RecipeLineOut]


def _recipe_out(db: Db, recipe: CuttingRecipe) -> RecipeOut:
    lines = service.recipe_lines(db, recipe.id)
    ids = {recipe.input_product_id, *(line.product_id for line in lines if line.product_id)}
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(ids)))}
    return RecipeOut(
        id=recipe.id,
        code=recipe.code,
        name=recipe.name,
        input_product_id=recipe.input_product_id,
        input_product_name=products[recipe.input_product_id].name,
        species=recipe.species,
        default_method=recipe.default_method,
        tolerance_kg=recipe.tolerance_kg,
        lines=[
            RecipeLineOut(
                id=line.id,
                line_type=line.line_type,
                product_id=line.product_id,
                product_code=products[line.product_id].code if line.product_id else None,
                product_name=products[line.product_id].name if line.product_id else None,
                standard_ratio=line.standard_ratio,
                value_per_kg=line.value_per_kg,
                bears_cost=line.bears_cost,
                sort_order=line.sort_order,
            )
            for line in lines
        ],
    )


@router.get("/cutting-recipes", response_model=list[RecipeOut])
def list_recipes(db: Db, _: WebUser) -> list[RecipeOut]:
    return [_recipe_out(db, r) for r in db.scalars(select(CuttingRecipe).order_by(CuttingRecipe.code))]


@router.get("/cutting-recipes/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: int, db: Db, _: WebUser) -> RecipeOut:
    return _recipe_out(db, get_or_404(db, CuttingRecipe, recipe_id, "Reçete"))


@router.post("/cutting-recipes", response_model=RecipeOut, status_code=201)
def create_recipe(body: RecipeIn, db: Db, user: ProductionUser) -> RecipeOut:
    recipe = service.create_recipe(
        db,
        code=body.code.strip(),
        name=body.name.strip(),
        input_product_id=body.input_product_id,
        species=body.species,
        default_method=body.default_method,
        tolerance_kg=body.tolerance_kg,
        lines=[service.RecipeLineInput(**line.model_dump()) for line in body.lines],
    )
    audit.log(
        db,
        "RECETE",
        f"Parçalama reçetesi {recipe.code} eklendi",
        user=user,
        ref_type="RECIPE",
        ref_id=recipe.id,
    )
    return _recipe_out(db, recipe)


# --- Parçalama ---


class CuttingIn(BaseModel):
    recipe_id: int
    input_lot_no: str
    input_qty: PositiveQty
    method: AllocationMethod | None = None  # boşsa reçetenin varsayılanı


class ActualIn(BaseModel):
    recipe_line_id: int
    actual_qty: NonNegativeQty | None  # boş: henüz tartılmadı


class ActualsIn(BaseModel):
    method: AllocationMethod | None = None
    outputs: list[ActualIn] = []


class BalanceOut(BaseModel):
    input_kg: Decimal
    outputs_kg: Decimal
    difference_kg: Decimal  # pozitif: çıkışlarda eksik kg
    tolerance_kg: Decimal
    ok: bool
    missing_lines: int  # fiili ağırlığı girilmemiş satır sayısı


class CuttingLineOut(BaseModel):
    output_id: int
    recipe_line_id: int
    line_type: RecipeLineType
    product_id: int | None
    product_code: str | None
    product_name: str | None
    standard_ratio: Decimal
    standard_kg: Decimal
    predicted_kg: Decimal | None
    actual_kg: Decimal | None
    value_per_kg: Decimal | None
    bears_cost: bool
    allocated_cost: Decimal | None
    cost_per_kg: Decimal | None
    output_lot_no: str | None


class InputCostOut(BaseModel):
    doc_no: str
    supplier_name: str
    qty: Decimal
    unit_price: Decimal
    computed_amount: Decimal
    invoice_amount: Decimal
    discrepancy_note: str | None
    extra_costs: list[ExtraCostOut]
    lot_value: Decimal


class CuttingOut(BaseModel):
    id: int
    cutting_no: str
    status: CuttingStatus
    recipe_id: int
    recipe_code: str
    recipe_name: str
    method: AllocationMethod
    input_lot_no: str
    input_product_name: str
    input_qty: Decimal
    total_cost: Decimal | None  # onaylıda kayıtlı; taslakta onaylanınca lottan çıkacak değer
    input_cost: InputCostOut | None
    balance: BalanceOut
    lines: list[CuttingLineOut]
    allocated_total: Decimal | None
    allocation_note: str | None
    cut_at: UtcDateTime
    approved_at: UtcDateTime | None


def _cutting_out(summary: service.CuttingSummary) -> CuttingOut:
    cutting, balance, cost = summary.cutting, summary.balance, summary.input_cost
    return CuttingOut(
        id=cutting.id,
        cutting_no=cutting.cutting_no,
        status=cutting.status,
        recipe_id=summary.recipe.id,
        recipe_code=summary.recipe.code,
        recipe_name=summary.recipe.name,
        method=summary.method,
        input_lot_no=summary.input_lot.lot_no,
        input_product_name=summary.input_product.name,
        input_qty=cutting.input_qty,
        total_cost=summary.total_cost,
        input_cost=InputCostOut(
            doc_no=cost.doc_no,
            supplier_name=cost.supplier_name,
            qty=cost.qty,
            unit_price=cost.unit_price,
            computed_amount=cost.computed_amount,
            invoice_amount=cost.invoice_amount,
            discrepancy_note=cost.discrepancy_note,
            extra_costs=[ExtraCostOut(kind=c.kind, amount=c.amount, note=c.note) for c in cost.extra_costs],
            lot_value=cost.lot_value,
        )
        if cost
        else None,
        balance=BalanceOut(
            input_kg=balance.input_kg,
            outputs_kg=balance.outputs_kg,
            difference_kg=balance.difference_kg,
            tolerance_kg=balance.tolerance_kg,
            ok=balance.ok and summary.missing_lines == 0,
            missing_lines=summary.missing_lines,
        ),
        lines=[
            CuttingLineOut(
                output_id=line.output_id,
                recipe_line_id=line.recipe_line_id,
                line_type=line.line_type,
                product_id=line.product.id if line.product else None,
                product_code=line.product.code if line.product else None,
                product_name=line.product.name if line.product else None,
                standard_ratio=line.standard_ratio,
                standard_kg=line.standard_kg,
                predicted_kg=line.predicted_kg,
                actual_kg=line.actual_kg,
                value_per_kg=line.value_per_kg,
                bears_cost=line.bears_cost,
                allocated_cost=line.allocated_cost,
                cost_per_kg=line.cost_per_kg,
                output_lot_no=line.output_lot_no,
            )
            for line in summary.lines
        ],
        allocated_total=summary.allocated_total,
        allocation_note=summary.allocation_note,
        cut_at=cutting.cut_at,
        approved_at=cutting.approved_at,
    )


def _actuals(body: ActualsIn) -> dict[int, Decimal | None]:
    return {item.recipe_line_id: item.actual_qty for item in body.outputs}


@router.post("/cuttings", response_model=CuttingOut, status_code=201)
def create(body: CuttingIn, db: Db, user: ProductionUser) -> CuttingOut:
    cutting = service.create_cutting(
        db,
        recipe_id=body.recipe_id,
        input_lot_id=lot_by_no(db, body.input_lot_no).id,
        input_qty=body.input_qty,
        method=body.method,
        user_id=user.id,
    )
    audit.log(
        db,
        "PARCALAMA",
        f"Parçalama {cutting.cutting_no} açıldı: {body.input_lot_no}, {tr_number(cutting.input_qty)} kg",
        user=user,
        ref_type="CUTTING",
        ref_id=cutting.id,
    )
    return _cutting_out(service.cutting_summary(db, cutting))


@router.get("/cuttings", response_model=list[CuttingOut])
def list_cuttings(db: Db, _: WebUser) -> list[CuttingOut]:
    cuttings = db.scalars(select(Cutting).order_by(Cutting.id.desc()))
    return [_cutting_out(service.cutting_summary(db, c)) for c in cuttings]


@router.get("/cuttings/{cutting_id}", response_model=CuttingOut)
def get_cutting(cutting_id: int, db: Db, _: WebUser) -> CuttingOut:
    return _cutting_out(service.cutting_summary(db, get_or_404(db, Cutting, cutting_id, "Parçalama")))


@router.put("/cuttings/{cutting_id}", response_model=CuttingOut)
def record_actuals(cutting_id: int, body: ActualsIn, db: Db, _: ProductionUser) -> CuttingOut:
    """Fiili kg'ları taslağa kaydeder (deftere yazmaz)."""
    cutting = service.record_actuals(db, cutting_id, actuals=_actuals(body), method=body.method)
    return _cutting_out(service.cutting_summary(db, cutting))


@router.post("/cuttings/{cutting_id}/preview", response_model=CuttingOut)
def preview(cutting_id: int, body: ActualsIn, db: Db, _: ProductionUser) -> CuttingOut:
    """Gönderilen kg'larla denge ve dağıtımı hesaplar; hiçbir şey kaydetmez."""
    cutting = get_or_404(db, Cutting, cutting_id, "Parçalama")
    return _cutting_out(service.cutting_summary(db, cutting, actuals=_actuals(body), method=body.method))


@router.post("/cuttings/{cutting_id}/approve", response_model=CuttingOut)
def approve(cutting_id: int, db: Db, user: ProductionUser) -> CuttingOut:
    cutting = service.approve_cutting(db, cutting_id, user_id=user.id)
    out = _cutting_out(service.cutting_summary(db, cutting))
    audit.log(
        db,
        "PARCALAMA_ONAY",
        f"Parçalama {cutting.cutting_no} onaylandı; parça lotları açıldı",
        user=user,
        ref_type="CUTTING",
        ref_id=cutting.id,
    )
    alarms.run_rules(db, user)  # fire sapması hemen görünsün
    return out
