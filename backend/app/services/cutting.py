"""Parçalama — Görev 2 (FR-201…FR-208, architecture.md §4.2).

Akış: taslak (reçetenin satırları açılır) → fiili kg'lar girilir → ön izleme (ağırlık dengesi +
dağıtım) → onay. Onay tek işlemdir (NFR-003): giriş lotundan tüketim, her parça ve yan ürün için
yeni lot (değeri = dağıtılan pay), lot bağları. Fire maliyet almaz; dağıtılan toplam = giriş
lotundan çıkan değer, kuruşu kuruşuna (en büyük kalan yöntemi, eşitlikte reçete sırası).
"""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.allocation import CuttingLine, allocate_cutting_cost
from app.domain.balance import WeightBalance, weight_balance
from app.domain.costing import outflow_value, unit_cost
from app.domain.money import round_qty, tr_number
from app.errors import InsufficientStock, InvalidInput, InvalidState, LotBlocked, NotFound, WeightImbalance
from app.models import (
    Cutting,
    CuttingOutput,
    CuttingRecipe,
    CuttingRecipeLine,
    Lot,
    Partner,
    Product,
    Purchase,
    PurchaseCost,
    PurchaseLine,
    StockBalance,
)
from app.models.enums import (
    AllocationMethod,
    BaseUnit,
    CuttingStatus,
    DocType,
    LinkProcess,
    LotOrigin,
    LotStatus,
    MovementType,
    PurchaseCostKind,
    RecipeLineType,
    Species,
)
from app.models.types import utcnow
from app.services.ledger import create_lot, post_movement
from app.services.lookups import get_or_404, main_warehouse
from app.services.lot_graph import link_lots
from app.services.numbering import next_document_no

# --- Reçete (FR-201, FR-202) ---


@dataclass(frozen=True)
class RecipeLineInput:
    line_type: RecipeLineType
    product_id: int | None
    standard_ratio: Decimal
    value_per_kg: Decimal | None = None
    bears_cost: bool = True


def create_recipe(
    session: Session,
    *,
    code: str,
    name: str,
    input_product_id: int,
    species: Species,
    default_method: AllocationMethod,
    tolerance_kg: Decimal,
    lines: Sequence[RecipeLineInput],
) -> CuttingRecipe:
    if session.scalar(select(CuttingRecipe.id).where(CuttingRecipe.code == code)) is not None:
        raise InvalidInput(f"Reçete kodu '{code}' zaten kullanılıyor.", code=code)
    input_product = get_or_404(session, Product, input_product_id, "Giriş ürünü")
    _require_kg(input_product)
    if tolerance_kg < 0:
        raise InvalidInput("Tartım toleransı eksi olamaz.")
    if not lines:
        raise InvalidInput("Reçetede en az bir çıkış satırı olmalı.")
    ratio_sum = sum((line.standard_ratio for line in lines), Decimal(0))
    if ratio_sum != 1:
        raise InvalidInput(
            f"Standart oranların toplamı 1 olmalı (şu an {tr_number(ratio_sum)}).", ratio_sum=ratio_sum
        )
    seen: set[int] = set()
    for line in lines:
        _check_recipe_line(session, line, default_method, seen)

    recipe = CuttingRecipe(
        code=code,
        name=name,
        input_product_id=input_product.id,
        species=species,
        default_method=default_method,
        tolerance_kg=tolerance_kg,
    )
    session.add(recipe)
    session.flush()
    session.add_all(
        CuttingRecipeLine(
            recipe_id=recipe.id,
            line_type=line.line_type,
            product_id=line.product_id,
            standard_ratio=line.standard_ratio,
            value_per_kg=line.value_per_kg,
            bears_cost=line.bears_cost and line.line_type != RecipeLineType.FIRE,
            sort_order=index,
        )
        for index, line in enumerate(lines, start=1)
    )
    session.flush()
    return recipe


def _check_recipe_line(
    session: Session, line: RecipeLineInput, method: AllocationMethod, seen: set[int]
) -> None:
    if not 0 <= line.standard_ratio <= 1:
        raise InvalidInput("Standart oran 0 ile 1 arasında olmalı.", ratio=line.standard_ratio)
    if line.value_per_kg is not None and line.value_per_kg < 0:
        raise InvalidInput("Değer katsayısı (€/kg) eksi olamaz.")
    if line.line_type == RecipeLineType.FIRE:
        if line.product_id is not None:
            raise InvalidInput("Fire satırına ürün bağlanmaz; fire stoka girmez ve maliyet almaz.")
        return
    if line.product_id is None:
        raise InvalidInput("Parça ve yan ürün satırlarında ürün seçilmeli.")
    product = get_or_404(session, Product, line.product_id, "Çıkış ürünü")
    _require_kg(product)
    if product.id in seen:
        raise InvalidInput(f"{product.name} reçetede birden fazla satırda var.", product=product.code)
    seen.add(product.id)
    if method == AllocationMethod.DEGER and line.bears_cost and line.value_per_kg is None:
        raise InvalidInput(f"Değer ağırlıklı reçetede {product.name} için €/kg değeri gerekli.")


def _require_kg(product: Product) -> None:
    if product.base_unit != BaseUnit.KG:
        raise InvalidInput(f"Parçalamada ürünler kg ile tartılır; {product.name} adet ile izleniyor.")


def recipe_lines(session: Session, recipe_id: int) -> list[CuttingRecipeLine]:
    return list(
        session.scalars(
            select(CuttingRecipeLine)
            .where(CuttingRecipeLine.recipe_id == recipe_id)
            .order_by(CuttingRecipeLine.sort_order)
        )
    )


# --- Parçalama işlemi (FR-203…FR-208) ---


def create_cutting(
    session: Session,
    *,
    recipe_id: int,
    input_lot_id: int,
    input_qty: Decimal,
    method: AllocationMethod | None = None,
    user_id: int | None = None,
) -> Cutting:
    """Taslak açar: reçetenin her satırı için boş bir çıkış satırı. Deftere henüz bir şey yazılmaz."""
    recipe = get_or_404(session, CuttingRecipe, recipe_id, "Reçete")
    lot = get_or_404(session, Lot, input_lot_id, "Giriş lotu")
    if lot.product_id != recipe.input_product_id:
        product = session.get(Product, recipe.input_product_id)
        raise InvalidInput(
            f"{lot.lot_no} bu reçetenin giriş ürünü ({product.name if product else '?'}) değil.",
            lot_no=lot.lot_no,
        )
    if lot.status == LotStatus.BLOKE:
        raise LotBlocked(f"{lot.lot_no} lotu bloke; parçalanamaz.", lot_no=lot.lot_no)
    if input_qty <= 0:
        raise InvalidInput("Giriş ağırlığı sıfırdan büyük olmalı.")
    available = _main_balance(session, lot)
    if input_qty > available:
        raise InsufficientStock(
            f"{lot.lot_no}: ana depoda {tr_number(available)} kg var; "
            f"{tr_number(input_qty)} kg parçalanamaz.",
            lot_no=lot.lot_no,
            available=available,
            requested=input_qty,
        )

    cutting = Cutting(
        cutting_no=next_document_no(session, "PRC", utcnow().year),
        recipe_id=recipe.id,
        input_lot_id=lot.id,
        input_qty=input_qty,
        species=recipe.species,
        method=method or recipe.default_method,
        created_by=user_id,
    )
    session.add(cutting)
    session.flush()
    session.add_all(
        CuttingOutput(
            cutting_id=cutting.id,
            recipe_line_id=line.id,
            line_type=line.line_type,
            product_id=line.product_id,
        )
        for line in recipe_lines(session, recipe.id)
    )
    session.flush()
    return cutting


def record_actuals(
    session: Session,
    cutting_id: int,
    *,
    actuals: Mapping[int, Decimal | None],
    method: AllocationMethod | None = None,
) -> Cutting:
    """Fiili kg'ları (recipe_line_id → kg) ve istenirse dağıtım yöntemini taslağa yazar."""
    cutting = _lock_cutting(session, cutting_id, action="tartım girişi")
    outputs = {output.recipe_line_id: output for output in _outputs(session, cutting)}
    _check_actuals(outputs, actuals)
    for line_id, qty in actuals.items():
        outputs[line_id].actual_qty = qty
    if method is not None:
        cutting.method = method
    session.flush()
    return cutting


def approve_cutting(session: Session, cutting_id: int, *, user_id: int | None = None) -> Cutting:
    """Onay: tüketim, dağıtım, parça lotları ve lot bağları — tek işlemde."""
    cutting = _lock_cutting(session, cutting_id, action="onay")
    recipe = session.get(CuttingRecipe, cutting.recipe_id)
    lines = {line.id: line for line in recipe_lines(session, cutting.recipe_id)}
    outputs = _outputs(session, cutting)
    assert recipe is not None
    if any(output.actual_qty is None for output in outputs):
        raise InvalidInput("Bütün satırların fiili ağırlığı girilmeli (fire yoksa 0 yazın).")
    balance = weight_balance(
        cutting.input_qty, [o.actual_qty or Decimal(0) for o in outputs], recipe.tolerance_kg
    )
    if not balance.ok:
        raise WeightImbalance(
            f"Ağırlık dengesi tutmuyor: giriş {tr_number(balance.input_kg)} kg, "
            f"çıkışlar {tr_number(balance.outputs_kg)} kg, fark {tr_number(balance.difference_kg)} kg "
            f"(tolerans {tr_number(balance.tolerance_kg)} kg). "
            "Eksik fire veya yan ürünü girin.",
            input_kg=balance.input_kg,
            outputs_kg=balance.outputs_kg,
            difference_kg=balance.difference_kg,
            tolerance_kg=balance.tolerance_kg,
        )
    if all((o.actual_qty or 0) == 0 for o in outputs if o.line_type != RecipeLineType.FIRE):
        raise InvalidInput("Parçalamadan en az bir parça çıkmalı.")

    main = main_warehouse(session)
    consumption = post_movement(
        session,
        lot_id=cutting.input_lot_id,
        warehouse_id=main.id,
        movement_type=MovementType.PARCALAMA_TUKETIM,
        qty=-cutting.input_qty,
        doc_type=DocType.PARCALAMA,
        doc_id=cutting.id,
        user_id=user_id,
    )
    total_cost = -consumption.value
    shares = allocate_cutting_cost(
        total_cost, [_cutting_line(o, lines[o.recipe_line_id]) for o in outputs], cutting.method
    )

    input_lot = session.get(Lot, cutting.input_lot_id)
    assert input_lot is not None
    today = utcnow().date()
    for output in outputs:
        output.allocated_cost = shares[output.id]
        qty = output.actual_qty or Decimal(0)
        if output.line_type == RecipeLineType.FIRE or qty == 0:
            continue
        product = session.get(Product, output.product_id)
        assert product is not None
        part_lot = create_lot(
            session,
            lot_no=f"{product.lot_prefix or product.code}-{cutting.cutting_no}",
            product_id=product.id,
            origin=LotOrigin.PARCALAMA,
            qty=qty,
            value=shares[output.id],
            warehouse_id=main.id,
            movement_type=MovementType.PARCALAMA_GIRIS,
            doc_type=DocType.PARCALAMA,
            doc_id=cutting.id,
            produced_at=today,
            expiry_date=_part_expiry(today, product, input_lot),
            user_id=user_id,
        )
        link_lots(
            session,
            parent_lot_id=input_lot.id,
            child_lot_id=part_lot.id,
            qty=qty,
            process=LinkProcess.PARCALAMA,
            process_id=cutting.id,
        )
        output.output_lot_id = part_lot.id

    cutting.total_cost = total_cost
    cutting.status = CuttingStatus.ONAYLANDI
    cutting.approved_at = utcnow()
    session.flush()
    return cutting


def _part_expiry(today: date, product: Product, input_lot: Lot) -> date | None:
    """Parçanın SKT'si kendi raf ömrüyle hesaplanır ama girdi lotunun SKT'sini geçemez."""
    own = today + timedelta(days=product.shelf_life_days) if product.shelf_life_days is not None else None
    dates = [d for d in (own, input_lot.expiry_date) if d is not None]
    return min(dates) if dates else None


# --- Okuma modeli: taslakta ön izleme, onaylıda kayıtlı sonuç ---


@dataclass(frozen=True)
class OutputLine:
    output_id: int
    recipe_line_id: int
    line_type: RecipeLineType
    product: Product | None
    standard_ratio: Decimal
    standard_kg: Decimal  # referans yöntem: standart oran × giriş (FR-503)
    predicted_kg: Decimal | None  # Model B (T-21)
    actual_kg: Decimal | None
    value_per_kg: Decimal | None
    bears_cost: bool
    allocated_cost: Decimal | None
    cost_per_kg: Decimal | None
    output_lot_no: str | None


@dataclass(frozen=True)
class ExtraCostItem:
    kind: PurchaseCostKind
    amount: Decimal
    note: str | None


@dataclass(frozen=True)
class InputCost:
    """Giriş lotunun alış maliyeti kalemleri (FR-203): fatura + ek maliyetler = lot değeri."""

    doc_no: str
    supplier_name: str
    qty: Decimal
    unit_price: Decimal
    computed_amount: Decimal
    invoice_amount: Decimal
    discrepancy_note: str | None
    extra_costs: list[ExtraCostItem]
    lot_value: Decimal


@dataclass(frozen=True)
class CuttingSummary:
    cutting: Cutting
    recipe: CuttingRecipe
    input_lot: Lot
    input_product: Product
    method: AllocationMethod
    total_cost: Decimal | None
    input_cost: InputCost | None
    balance: WeightBalance
    missing_lines: int
    lines: list[OutputLine]
    allocated_total: Decimal | None
    allocation_note: str | None


def cutting_summary(
    session: Session,
    cutting: Cutting,
    *,
    actuals: Mapping[int, Decimal | None] | None = None,
    method: AllocationMethod | None = None,
) -> CuttingSummary:
    """Parçalamanın görünümü. Taslakta `actuals`/`method` verilirse kaydetmeden onlarla hesaplar."""
    recipe = session.get(CuttingRecipe, cutting.recipe_id)
    input_lot = session.get(Lot, cutting.input_lot_id)
    assert recipe is not None and input_lot is not None
    input_product = session.get(Product, input_lot.product_id)
    assert input_product is not None
    lines = {line.id: line for line in recipe_lines(session, recipe.id)}
    outputs = _outputs(session, cutting)
    approved = cutting.status == CuttingStatus.ONAYLANDI
    overrides = {} if approved or actuals is None else dict(actuals)
    if overrides:
        _check_actuals({o.recipe_line_id: o for o in outputs}, overrides)
    used_method = cutting.method if approved or method is None else method

    def actual_of(output: CuttingOutput) -> Decimal | None:
        return overrides.get(output.recipe_line_id, output.actual_qty) if overrides else output.actual_qty

    total_cost = cutting.total_cost if approved else _expected_cost(input_lot, cutting.input_qty)
    missing = sum(1 for o in outputs if actual_of(o) is None)
    balance = weight_balance(
        cutting.input_qty, [actual_of(o) or Decimal(0) for o in outputs], recipe.tolerance_kg
    )

    shares: Mapping[Hashable, Decimal] = {}
    note = None
    if approved:
        shares = {o.id: o.allocated_cost for o in outputs if o.allocated_cost is not None}
    elif total_cost is None:
        note = "Giriş lotunda bu kadar miktar kalmadı; maliyet hesaplanamıyor."
    elif missing:
        note = "Dağıtım, bütün satırların fiili ağırlığı girilince hesaplanır."
    else:
        try:
            shares = allocate_cutting_cost(
                total_cost,
                [_cutting_line(o, lines[o.recipe_line_id], actual_of(o)) for o in outputs],
                used_method,
            )
        except InvalidInput as error:
            note = error.message

    lot_nos = _lot_numbers(session, [o.output_lot_id for o in outputs if o.output_lot_id])
    products = _products(session, [o.product_id for o in outputs if o.product_id])
    result = []
    for output in outputs:
        line = lines[output.recipe_line_id]
        actual = actual_of(output)
        share = shares.get(output.id)
        result.append(
            OutputLine(
                output_id=output.id,
                recipe_line_id=line.id,
                line_type=output.line_type,
                product=products.get(output.product_id) if output.product_id else None,
                standard_ratio=line.standard_ratio,
                standard_kg=round_qty(line.standard_ratio * cutting.input_qty),
                predicted_kg=output.predicted_qty,
                actual_kg=actual,
                value_per_kg=line.value_per_kg,
                bears_cost=line.bears_cost,
                allocated_cost=share,
                cost_per_kg=unit_cost(share, actual)
                if line.bears_cost and share is not None and actual
                else None,
                output_lot_no=lot_nos.get(output.output_lot_id) if output.output_lot_id else None,
            )
        )
    return CuttingSummary(
        cutting=cutting,
        recipe=recipe,
        input_lot=input_lot,
        input_product=input_product,
        method=used_method,
        total_cost=total_cost,
        input_cost=_input_cost(session, input_lot),
        balance=balance,
        missing_lines=missing,
        lines=result,
        allocated_total=sum(shares.values(), Decimal("0.00")) if shares else None,
        allocation_note=note,
    )


def _expected_cost(lot: Lot, qty: Decimal) -> Decimal | None:
    """Taslakta: onaylanınca giriş lotundan çıkacak değer (kalan değerin orantılı payı)."""
    if qty > lot.remaining_qty:
        return None
    return outflow_value(lot.remaining_qty, lot.remaining_value, qty)


def _input_cost(session: Session, lot: Lot) -> InputCost | None:
    if lot.origin != LotOrigin.ALIS:
        return None
    line = session.scalars(select(PurchaseLine).where(PurchaseLine.lot_id == lot.id)).first()
    if line is None:
        return None
    purchase = session.get(Purchase, line.purchase_id)
    assert purchase is not None
    supplier = session.get(Partner, purchase.supplier_id)
    costs = session.scalars(
        select(PurchaseCost).where(PurchaseCost.purchase_line_id == line.id).order_by(PurchaseCost.id)
    ).all()
    return InputCost(
        doc_no=purchase.doc_no,
        supplier_name=supplier.name if supplier else "",
        qty=line.qty,
        unit_price=line.unit_price,
        computed_amount=line.computed_amount,
        invoice_amount=line.invoice_amount,
        discrepancy_note=line.discrepancy_note,
        extra_costs=[ExtraCostItem(kind=c.kind, amount=c.amount, note=c.note) for c in costs],
        lot_value=lot.initial_value,
    )


# --- Yardımcılar ---


def _cutting_line(
    output: CuttingOutput, line: CuttingRecipeLine, actual: Decimal | None = None
) -> CuttingLine:
    qty = actual if actual is not None else output.actual_qty
    return CuttingLine(
        key=output.id,
        line_type=output.line_type,
        actual_kg=qty or Decimal(0),
        value_per_kg=line.value_per_kg,
        bears_cost=line.bears_cost,
    )


def _check_actuals(outputs: Mapping[int, CuttingOutput], actuals: Mapping[int, Decimal | None]) -> None:
    unknown = set(actuals) - set(outputs)
    if unknown:
        raise InvalidInput(
            "Bu parçalamada olmayan reçete satırı gönderildi.", recipe_line_ids=sorted(unknown)
        )
    if any(qty is not None and qty < 0 for qty in actuals.values()):
        raise InvalidInput("Fiili ağırlık eksi olamaz.")


def _main_balance(session: Session, lot: Lot) -> Decimal:
    balance = session.get(StockBalance, (lot.id, main_warehouse(session).id))
    return balance.qty if balance else Decimal(0)


def _outputs(session: Session, cutting: Cutting) -> list[CuttingOutput]:
    return list(
        session.scalars(
            select(CuttingOutput)
            .join(CuttingRecipeLine, CuttingRecipeLine.id == CuttingOutput.recipe_line_id)
            .where(CuttingOutput.cutting_id == cutting.id)
            .order_by(CuttingRecipeLine.sort_order)
        )
    )


def _lot_numbers(session: Session, lot_ids: list[int]) -> dict[int, str]:
    if not lot_ids:
        return {}
    rows = session.execute(select(Lot.id, Lot.lot_no).where(Lot.id.in_(lot_ids)))
    return {lot_id: lot_no for lot_id, lot_no in rows}


def _products(session: Session, product_ids: list[int]) -> dict[int, Product]:
    if not product_ids:
        return {}
    return {p.id: p for p in session.scalars(select(Product).where(Product.id.in_(product_ids)))}


def _lock_cutting(session: Session, cutting_id: int, *, action: str) -> Cutting:
    cutting = session.execute(
        select(Cutting)
        .where(Cutting.id == cutting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if cutting is None:
        raise NotFound("Parçalama bulunamadı.", id=cutting_id)
    if cutting.status != CuttingStatus.TASLAK:
        raise InvalidState(
            f"{cutting.cutting_no} onaylanmış; {action} yalnız taslakta yapılabilir.",
            cutting_no=cutting.cutting_no,
            status=cutting.status,
        )
    return cutting
