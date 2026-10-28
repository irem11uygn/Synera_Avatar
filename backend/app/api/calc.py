"""Ne olur hesaplayıcıları: kayıt açmadan EKP ve parçalama maliyeti.

Hesap, gerçek kayıtlarda kullanılan aynı fonksiyonlarla yapılır (app/domain): hesaplayıcıda çıkan
EKP ve parça maliyetleri, aynı değerlerle açılan emir ve parçalamada kuruşu kuruşuna aynıdır.
"""

from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import WebUser
from app.domain.allocation import CuttingLine, allocate_cutting_cost
from app.domain.balance import weight_balance
from app.domain.costing import line_amount, production_cost, profitability
from app.domain.money import round_money, round_percent, round_unit_cost, tr_number
from app.models.enums import AllocationMethod, RecipeLineType

router = APIRouter(prefix="/calc", tags=["hesaplayıcı"])


class RawLineIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    qty: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=4)


class EkpIn(BaseModel):
    raw_lines: list[RawLineIn] = Field(min_length=1, max_length=30)
    service_unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    received_qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    invoiced_qty: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    service_invoice_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    sale_price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)


class RawLineOut(BaseModel):
    name: str
    qty: Decimal
    unit_price: Decimal
    amount: Decimal


class EkpOut(BaseModel):
    raw_lines: list[RawLineOut]
    raw_total: Decimal
    service_suggested: Decimal
    service_used: Decimal
    total: Decimal
    ekp: Decimal
    ekp_display: Decimal
    gross_profit_per_unit: Decimal | None
    margin_pct: Decimal | None
    total_gross_profit: Decimal | None
    warnings: list[str]


@router.post("/ekp", response_model=EkpOut)
def ekp(body: EkpIn, _: WebUser) -> EkpOut:
    lines = [
        RawLineOut(name=r.name, qty=r.qty, unit_price=r.unit_price, amount=line_amount(r.qty, r.unit_price))
        for r in body.raw_lines
    ]
    suggested = line_amount(body.received_qty, body.service_unit_price)  # emir tamamlamadaki kural
    used = body.service_invoice_amount if body.service_invoice_amount is not None else suggested
    cost = production_cost([line.amount for line in lines], used, body.received_qty)
    warnings: list[str] = []
    if body.invoiced_qty is not None and body.invoiced_qty != body.received_qty:
        warnings.append(
            f"Dış üreticinin faturasında {tr_number(body.invoiced_qty)} adet var, teslim alınan "
            f"{tr_number(body.received_qty)}. Hizmet bedeli teslim alınan adet üzerinden önerilir; farkı "
            "dış üreticiyle netleştirin."
        )
    if body.service_invoice_amount is not None and body.service_invoice_amount != suggested:
        warnings.append(
            f"Hizmet faturası {tr_number(body.service_invoice_amount, 2)} €, adet × ücret "
            f"{tr_number(suggested, 2)} €. Gerçek kayıtta bu fark için açıklama zorunludur."
        )
    profit = margin = total_profit = None
    if body.sale_price is not None:
        result = profitability(body.sale_price, cost.ekp)
        profit, margin = result.gross_profit_per_unit, result.margin_pct
        total_profit = round_money(body.sale_price * body.received_qty - cost.total)
        if profit < 0:
            warnings.append("Satış fiyatı birim maliyetin altında: her satışta zarar edilir.")
    return EkpOut(
        raw_lines=lines,
        raw_total=cost.raw_materials,
        service_suggested=suggested,
        service_used=used,
        total=cost.total,
        ekp=cost.ekp,
        ekp_display=cost.ekp_display,
        gross_profit_per_unit=profit,
        margin_pct=margin,
        total_gross_profit=total_profit,
        warnings=warnings,
    )


class CutLineIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kg: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    value_per_kg: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=4)
    is_fire: bool = False
    bears_cost: bool = True


class CuttingCalcIn(BaseModel):
    input_kg: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    input_cost: Decimal = Field(ge=0, max_digits=14, decimal_places=2)  # alış + ek maliyetler
    invoice_kg: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    method: AllocationMethod
    tolerance_kg: Decimal = Field(default=Decimal("0.5"), ge=0, max_digits=6, decimal_places=3)
    lines: list[CutLineIn] = Field(min_length=1, max_length=30)


class CutLineOut(BaseModel):
    name: str
    kg: Decimal
    share_pct: Decimal
    allocated_cost: Decimal
    unit_cost: Decimal | None
    is_fire: bool


class CuttingCalcOut(BaseModel):
    lines: list[CutLineOut]
    outputs_kg: Decimal
    fire_kg: Decimal
    fire_pct: Decimal
    difference_kg: Decimal
    balance_ok: bool
    total_allocated: Decimal
    input_unit_cost: Decimal
    warnings: list[str]


@router.post("/cutting", response_model=CuttingCalcOut)
def cutting(body: CuttingCalcIn, _: WebUser) -> CuttingCalcOut:
    total = round_money(body.input_cost)
    domain_lines = [
        CuttingLine(
            key=i,
            line_type=RecipeLineType.FIRE if line.is_fire else RecipeLineType.PARCA,
            actual_kg=line.kg,
            value_per_kg=line.value_per_kg,
            bears_cost=line.bears_cost,
        )
        for i, line in enumerate(body.lines)
    ]
    shares = allocate_cutting_cost(total, domain_lines, body.method)
    balance = weight_balance(body.input_kg, [line.kg for line in body.lines], body.tolerance_kg)
    fire_kg = sum((line.kg for line in body.lines if line.is_fire), Decimal(0))
    warnings: list[str] = []
    if not balance.ok:
        warnings.append(
            f"Ağırlık dengesi tutmuyor: giriş {tr_number(balance.input_kg)} kg, çıkışlar "
            f"{tr_number(balance.outputs_kg)} kg, fark {tr_number(balance.difference_kg)} kg (tolerans "
            f"{tr_number(body.tolerance_kg)} kg). Sistem bu parçalamayı onaylamaz; tartımı kontrol edin."
        )
    if body.invoice_kg is not None and body.invoice_kg != body.input_kg:
        warnings.append(
            f"Faturadaki ağırlık {tr_number(body.invoice_kg)} kg, "
            f"tartılan giriş {tr_number(body.input_kg)} kg: "
            "belge ile tartım tutarsız; tedarikçiyle netleştirin."
        )
    zero = [line.name for line in body.lines if not line.is_fire and line.kg == 0]
    if zero:
        warnings.append(f"Ağırlığı sıfır olan parça: {', '.join(zero)} (maliyet almaz, lot açılmaz).")
    return CuttingCalcOut(
        lines=[
            CutLineOut(
                name=line.name,
                kg=line.kg,
                share_pct=round_percent(line.kg / body.input_kg * 100),
                allocated_cost=shares[i],
                unit_cost=round_unit_cost(shares[i] / line.kg) if line.kg > 0 and not line.is_fire else None,
                is_fire=line.is_fire,
            )
            for i, line in enumerate(body.lines)
        ],
        outputs_kg=balance.outputs_kg,
        fire_kg=fire_kg,
        fire_pct=round_percent(fire_kg / body.input_kg * 100),
        difference_kg=balance.difference_kg,
        balance_ok=balance.ok,
        total_allocated=sum(shares.values(), Decimal("0.00")),
        input_unit_cost=round_unit_cost(total / body.input_kg),
        warnings=warnings,
    )
