"""Raporlar (FR-601…FR-607): alış, üretim, parçalama, lot hareketleri, satış, geri çağırma, bütünlük.

Her rapor aynı biçimde döner: sütun tanımları + satırlar (+ toplamlar, notlar). Web tek bir rapor
ekranıyla hepsini gösterir; CSV aynı veriden üretilir. Değerler ham (Decimal, tarih) tutulur;
JSON ve CSV biçimine API katmanında çevrilir.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.money import round_money, round_percent
from app.models import (
    Cutting,
    Lot,
    Partner,
    Product,
    ProductionOrder,
    Purchase,
    PurchaseCost,
    PurchaseLine,
    Recall,
    Sale,
    SaleLine,
    StockMovement,
    User,
    Warehouse,
)
from app.models.enums import BaseUnit, ForecastTarget, RecipeLineType
from app.services.ai import first_forecast
from app.services.cutting import cutting_summary
from app.services.integrity import check_invariants
from app.services.lookups import document_numbers
from app.services.production import order_summary
from app.services.recall import recall_view
from app.services.trace import returned_qty_by_line

MAX_ROWS = 5000


class ReportCode(StrEnum):
    PURCHASES = "purchases"
    PRODUCTION = "production"
    CUTTINGS = "cuttings"
    LOT_MOVEMENTS = "lot-movements"
    SALES = "sales"
    RECALLS = "recalls"
    INTEGRITY = "integrity"


class ColumnKind(StrEnum):
    TEXT = "text"
    QTY = "qty"
    MONEY = "money"
    UNIT_COST = "unit_cost"
    PERCENT = "percent"
    DATE = "date"
    DATETIME = "datetime"
    BOOL = "bool"
    STATUS = "status"


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    kind: ColumnKind = ColumnKind.TEXT


@dataclass(frozen=True)
class ReportFilter:
    date_from: date | None = None
    date_to: date | None = None
    product_id: int | None = None
    lot_no: str | None = None


@dataclass
class Report:
    code: ReportCode
    title: str
    description: str
    columns: list[Column]
    rows: list[dict[str, Any]]
    totals: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# Rapor adı ve açıklaması (rapor listesi ve rapor başlığı aynı yerden okur).
META: dict[ReportCode, tuple[str, str]] = {
    ReportCode.PURCHASES: (
        "Alış raporu",
        "Tedarikçi, lot, miktar ve tutar; lot değeri = fatura + ek maliyetler (FR-601).",
    ),
    ReportCode.PRODUCTION: (
        "Üretim raporu",
        "Emir, girdiler, mamul, miktar farkları, gerçek birim maliyet (EKP), kâr/marj ve "
        "Model A tahmini–gerçek–sapma (FR-602, FR-109, FR-502).",
    ),
    ReportCode.CUTTINGS: (
        "Parçalama raporu",
        "Giriş, parçalar, fire, maliyet dağıtımı; standart oran, Model B tahmini ve gerçek kg farkı "
        "(FR-603, FR-504).",
    ),
    ReportCode.LOT_MOVEMENTS: (
        "Lot hareketleri raporu",
        "Lot bazlı bütün hareketler ve yürüyen bakiye; bakiye = hareketlerin toplamı (FR-604).",
    ),
    ReportCode.SALES: (
        "Satış raporu",
        "Müşteri, ürün, lot, miktar, tutar, maliyet, brüt kâr ve kanal (FR-605).",
    ),
    ReportCode.RECALLS: (
        "Geri çağırma raporu",
        "Etkilenen lotlar, alıcılar, müşteride kalan miktarlar ve durum (FR-606).",
    ),
    ReportCode.INTEGRITY: (
        "Bütünlük raporu",
        "Defter ile özetlerin tutarlılığı: değişmezler I-1…I-8 (FR-607, data_model.md §5).",
    ),
}


def build_report(session: Session, code: ReportCode, filters: ReportFilter) -> Report:
    report = _BUILDERS[code](session, filters)
    if len(report.rows) > MAX_ROWS:
        report.notes.append(f"İlk {MAX_ROWS} satır gösteriliyor; süzgeçleri daraltın.")
        report.rows = report.rows[:MAX_ROWS]
    return report


def _day_range(column: Any, filters: ReportFilter) -> list[Any]:
    """Tarih süzgeci: date_to günü dahil (sütun tarih-saatse ertesi gün başına kadar)."""
    conditions = []
    if filters.date_from:
        conditions.append(column >= datetime.combine(filters.date_from, time.min))
    if filters.date_to:
        conditions.append(column < datetime.combine(filters.date_to + timedelta(days=1), time.min))
    return conditions


def _unit(base_unit: BaseUnit) -> str:
    return "kg" if base_unit == BaseUnit.KG else "adet"


def _total(rows: list[dict[str, Any]], key: str) -> Decimal:
    return sum((row[key] for row in rows if row.get(key) is not None), Decimal(0))


# --- FR-601 Alış ---


def _purchases(session: Session, f: ReportFilter) -> Report:
    extra = (
        select(PurchaseCost.purchase_line_id, func.sum(PurchaseCost.amount).label("amount"))
        .group_by(PurchaseCost.purchase_line_id)
        .subquery()
    )
    query: Select = (
        select(PurchaseLine, Purchase, Partner.name, Product, Lot, extra.c.amount)
        .join(Purchase, Purchase.id == PurchaseLine.purchase_id)
        .join(Partner, Partner.id == Purchase.supplier_id)
        .join(Product, Product.id == PurchaseLine.product_id)
        .join(Lot, Lot.id == PurchaseLine.lot_id)
        .outerjoin(extra, extra.c.purchase_line_id == PurchaseLine.id)
        .order_by(Purchase.doc_date, Purchase.id, PurchaseLine.id)
    )
    if f.date_from:
        query = query.where(Purchase.doc_date >= f.date_from)
    if f.date_to:
        query = query.where(Purchase.doc_date <= f.date_to)
    if f.product_id:
        query = query.where(PurchaseLine.product_id == f.product_id)
    if f.lot_no:
        query = query.where(Lot.lot_no.contains(f.lot_no))
    rows = [
        {
            "doc_date": purchase.doc_date,
            "doc_no": purchase.doc_no,
            "supplier": supplier,
            "product": product.name,
            "lot_no": lot.lot_no,
            "qty": line.qty,
            "unit": _unit(product.base_unit),
            "unit_price": line.unit_price,
            "invoice_amount": line.invoice_amount,
            "extra_costs": extra_amount or Decimal("0.00"),
            "lot_value": lot.initial_value,
            "unit_cost": lot.unit_cost,
            "note": line.discrepancy_note,
        }
        for line, purchase, supplier, product, lot, extra_amount in session.execute(query)
    ]
    return Report(
        code=ReportCode.PURCHASES,
        title=META[ReportCode.PURCHASES][0],
        description=META[ReportCode.PURCHASES][1],
        columns=[
            Column("doc_date", "Tarih", ColumnKind.DATE),
            Column("doc_no", "Belge"),
            Column("supplier", "Tedarikçi"),
            Column("product", "Ürün"),
            Column("lot_no", "Lot"),
            Column("qty", "Miktar", ColumnKind.QTY),
            Column("unit", "Birim"),
            Column("unit_price", "Birim fiyat", ColumnKind.UNIT_COST),
            Column("invoice_amount", "Fatura", ColumnKind.MONEY),
            Column("extra_costs", "Ek maliyet", ColumnKind.MONEY),
            Column("lot_value", "Lot değeri", ColumnKind.MONEY),
            Column("unit_cost", "Birim maliyet", ColumnKind.UNIT_COST),
            Column("note", "Fatura farkı açıklaması"),
        ],
        rows=rows,
        totals={key: _total(rows, key) for key in ("invoice_amount", "extra_costs", "lot_value")},
    )


# --- FR-602 Üretim (+ FR-109 farklar, FR-502 YZ tahmini) ---


def _dec(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _production(session: Session, f: ReportFilter) -> Report:
    query = select(ProductionOrder).order_by(ProductionOrder.ordered_at, ProductionOrder.id)
    query = query.where(*_day_range(ProductionOrder.ordered_at, f))
    if f.product_id:
        query = query.where(ProductionOrder.output_product_id == f.product_id)
    rows = []
    for order in session.scalars(query):
        s = order_summary(session, order)
        if f.lot_no and not (
            (s.output_lot_no and f.lot_no in s.output_lot_no) or any(f.lot_no in i.lot_no for i in s.inputs)
        ):
            continue
        forecast = first_forecast(session, ForecastTarget.URETIM_EMRI, order.id)
        expected = _dec(forecast.prediction.get("expected_qty")) if forecast else None
        forecast_ekp = _dec(forecast.prediction.get("ekp")) if forecast else None
        ekp = s.cost.ekp_display if s.cost else None
        received = order.received_qty
        rows.append(
            {
                "order_no": order.order_no,
                "ordered_at": order.ordered_at,
                "status": order.status,
                "subcontractor": s.subcontractor.name,
                "product": s.product.name,
                "planned_qty": order.planned_qty,
                "received_qty": received,
                "qty_difference": received - order.planned_qty if received is not None else None,
                "input_differences": "; ".join(
                    f"{i.lot_no}: sevk {i.shipped_qty.normalize():f} / tüketim {i.consumed_qty.normalize():f}"
                    f" / iade {i.returned_qty.normalize():f}"
                    for i in s.inputs
                ),
                "raw_materials": s.cost.raw_materials if s.cost else None,
                "service": s.cost.service if s.cost else None,
                "total_cost": s.cost.total if s.cost else None,
                "ekp": ekp,
                "sale_price": s.product.sale_price,
                "gross_profit": s.sales.gross_profit_per_unit if s.sales else None,
                "margin_pct": s.sales.margin_pct if s.sales else None,
                "yield_main_pct": s.yield_.yield_main_pct if s.yield_ else None,
                "ai_expected_qty": expected,
                "ai_qty_deviation": received - expected
                if received is not None and expected is not None
                else None,
                "ai_ekp": forecast_ekp,
                "ai_ekp_deviation": (
                    round_money(ekp - forecast_ekp) if ekp is not None and forecast_ekp is not None else None
                ),
                "output_lot_no": s.output_lot_no,
            }
        )
    return Report(
        code=ReportCode.PRODUCTION,
        title=META[ReportCode.PRODUCTION][0],
        description=META[ReportCode.PRODUCTION][1],
        columns=[
            Column("order_no", "Emir"),
            Column("ordered_at", "Tarih", ColumnKind.DATE),
            Column("status", "Durum", ColumnKind.STATUS),
            Column("subcontractor", "Dış üretici"),
            Column("product", "Mamul"),
            Column("planned_qty", "Planlanan", ColumnKind.QTY),
            Column("received_qty", "Teslim alınan", ColumnKind.QTY),
            Column("qty_difference", "Miktar farkı", ColumnKind.QTY),
            Column("input_differences", "Girdiler: sevk / tüketim / iade"),
            Column("raw_materials", "Hammadde", ColumnKind.MONEY),
            Column("service", "Hizmet", ColumnKind.MONEY),
            Column("total_cost", "Toplam maliyet", ColumnKind.MONEY),
            Column("ekp", "EKP", ColumnKind.MONEY),
            Column("sale_price", "VKP", ColumnKind.MONEY),
            Column("gross_profit", "Birim brüt kâr", ColumnKind.MONEY),
            Column("margin_pct", "Marj %", ColumnKind.PERCENT),
            Column("yield_main_pct", "Et bazlı verim %", ColumnKind.PERCENT),
            Column("ai_expected_qty", "YZ tahmini miktar", ColumnKind.QTY),
            Column("ai_qty_deviation", "Miktar sapması", ColumnKind.QTY),
            Column("ai_ekp", "YZ tahmini EKP", ColumnKind.MONEY),
            Column("ai_ekp_deviation", "EKP sapması", ColumnKind.MONEY),
            Column("output_lot_no", "Mamul lotu"),
        ],
        rows=rows,
        totals={key: _total(rows, key) for key in ("raw_materials", "service", "total_cost")},
    )


# --- FR-603 Parçalama (+ FR-504 YZ tahmini/fark) ---


def _cuttings(session: Session, f: ReportFilter) -> Report:
    query = select(Cutting).order_by(Cutting.cut_at, Cutting.id).where(*_day_range(Cutting.cut_at, f))
    rows = []
    for cutting in session.scalars(query):
        s = cutting_summary(session, cutting)
        lot_nos = [s.input_lot.lot_no, *(line.output_lot_no or "" for line in s.lines)]
        if f.lot_no and not any(f.lot_no in no for no in lot_nos):
            continue
        product_ids = {s.input_product.id, *(line.product.id for line in s.lines if line.product)}
        if f.product_id and f.product_id not in product_ids:
            continue
        for line in s.lines:
            name = line.product.name if line.product else "Fire"
            if line.line_type == RecipeLineType.YAN_URUN and line.product:
                name = f"{line.product.name} (yan ürün)"
            rows.append(
                {
                    "cutting_no": cutting.cutting_no,
                    "cut_at": cutting.cut_at,
                    "status": cutting.status,
                    "input_lot_no": s.input_lot.lot_no,
                    "input_qty": cutting.input_qty,
                    "method": s.method,
                    "line": name,
                    "standard_kg": line.standard_kg,
                    "predicted_kg": line.predicted_kg,
                    "actual_kg": line.actual_kg,
                    "ai_difference": (
                        line.actual_kg - line.predicted_kg
                        if line.actual_kg is not None and line.predicted_kg is not None
                        else None
                    ),
                    "allocated_cost": line.allocated_cost,
                    "cost_per_kg": line.cost_per_kg,
                    "output_lot_no": line.output_lot_no,
                }
            )
    return Report(
        code=ReportCode.CUTTINGS,
        title=META[ReportCode.CUTTINGS][0],
        description=META[ReportCode.CUTTINGS][1],
        columns=[
            Column("cutting_no", "Parçalama"),
            Column("cut_at", "Tarih", ColumnKind.DATE),
            Column("status", "Durum", ColumnKind.STATUS),
            Column("input_lot_no", "Giriş lotu"),
            Column("input_qty", "Giriş kg", ColumnKind.QTY),
            Column("method", "Dağıtım", ColumnKind.STATUS),
            Column("line", "Parça"),
            Column("standard_kg", "Standart kg", ColumnKind.QTY),
            Column("predicted_kg", "YZ tahmini kg", ColumnKind.QTY),
            Column("actual_kg", "Gerçek kg", ColumnKind.QTY),
            Column("ai_difference", "Gerçek − tahmin", ColumnKind.QTY),
            Column("allocated_cost", "Dağıtılan maliyet", ColumnKind.MONEY),
            Column("cost_per_kg", "Maliyet / kg", ColumnKind.UNIT_COST),
            Column("output_lot_no", "Parça lotu"),
        ],
        rows=rows,
        totals={"allocated_cost": _total(rows, "allocated_cost")},
    )


# --- FR-604 Lot hareketleri ---


def _lot_movements(session: Session, f: ReportFilter) -> Report:
    query = (
        select(StockMovement, Lot.lot_no, Product, Warehouse.code, User.full_name)
        .join(Lot, Lot.id == StockMovement.lot_id)
        .join(Product, Product.id == StockMovement.product_id)
        .join(Warehouse, Warehouse.id == StockMovement.warehouse_id)
        .outerjoin(User, User.id == StockMovement.user_id)
        .order_by(StockMovement.lot_id, StockMovement.id)
    )
    if f.product_id:
        query = query.where(StockMovement.product_id == f.product_id)
    if f.lot_no:
        query = query.where(Lot.lot_no.contains(f.lot_no))
    result = session.execute(query).all()
    numbers = document_numbers(session, ((m.doc_type, m.doc_id) for m, *_ in result))
    running_qty: dict[int, Decimal] = defaultdict(Decimal)
    running_value: dict[int, Decimal] = defaultdict(Decimal)
    start = datetime.combine(f.date_from, time.min) if f.date_from else None
    end = datetime.combine(f.date_to + timedelta(days=1), time.min) if f.date_to else None
    rows = []
    for movement, lot_no, product, warehouse, user in result:
        running_qty[movement.lot_id] += movement.qty
        running_value[movement.lot_id] += movement.value
        if (start and movement.posted_at < start) or (end and movement.posted_at >= end):
            continue  # bakiye tarih süzgecinden önceki hareketleri de sayar
        rows.append(
            {
                "posted_at": movement.posted_at,
                "lot_no": lot_no,
                "product": product.name,
                "type": movement.type,
                "warehouse": warehouse,
                "qty": movement.qty,
                "unit": _unit(product.base_unit),
                "value": movement.value,
                "doc_no": numbers.get((movement.doc_type, movement.doc_id)),
                "balance_qty": running_qty[movement.lot_id],
                "balance_value": running_value[movement.lot_id],
                "user": user,
                "note": movement.note,
            }
        )
    rows.sort(key=lambda row: row["posted_at"])
    return Report(
        code=ReportCode.LOT_MOVEMENTS,
        title=META[ReportCode.LOT_MOVEMENTS][0],
        description=META[ReportCode.LOT_MOVEMENTS][1],
        columns=[
            Column("posted_at", "Zaman", ColumnKind.DATETIME),
            Column("lot_no", "Lot"),
            Column("product", "Ürün"),
            Column("type", "Hareket", ColumnKind.STATUS),
            Column("warehouse", "Depo"),
            Column("qty", "Miktar", ColumnKind.QTY),
            Column("unit", "Birim"),
            Column("value", "Değer", ColumnKind.MONEY),
            Column("doc_no", "Belge"),
            Column("balance_qty", "Lot bakiyesi", ColumnKind.QTY),
            Column("balance_value", "Lot değeri", ColumnKind.MONEY),
            Column("user", "Kullanıcı"),
            Column("note", "Not"),
        ],
        rows=rows,
    )


# --- FR-605 Satış ---


def _sales(session: Session, f: ReportFilter) -> Report:
    query = (
        select(SaleLine, Sale, Partner.name, Lot.lot_no, Product)
        .join(Sale, Sale.id == SaleLine.sale_id)
        .join(Partner, Partner.id == Sale.customer_id)
        .join(Lot, Lot.id == SaleLine.lot_id)
        .join(Product, Product.id == SaleLine.product_id)
        .where(*_day_range(Sale.received_at, f))
        .order_by(Sale.received_at, Sale.id, SaleLine.line_no)
    )
    if f.product_id:
        query = query.where(SaleLine.product_id == f.product_id)
    if f.lot_no:
        query = query.where(Lot.lot_no.contains(f.lot_no))
    result = session.execute(query).all()
    returned = returned_qty_by_line(session, [line.id for line, *_ in result])
    rows = []
    for line, sale, customer, lot_no, product in result:
        profit = line.amount - line.cost_amount
        rows.append(
            {
                "sold_at": sale.sold_at,
                "sale_no": sale.sale_no,
                "channel": sale.channel,
                "customer": customer,
                "product": product.name,
                "lot_no": lot_no,
                "qty": line.qty,
                "unit": _unit(product.base_unit),
                "unit_price": line.unit_price,
                "amount": line.amount,
                "cost": line.cost_amount,
                "gross_profit": profit,
                "margin_pct": round_percent(profit * 100 / line.amount) if line.amount else None,
                "returned_qty": returned.get(line.id, Decimal(0)),
                "recall_violation": sale.recall_violation,
            }
        )
    return Report(
        code=ReportCode.SALES,
        title=META[ReportCode.SALES][0],
        description=META[ReportCode.SALES][1],
        columns=[
            Column("sold_at", "Satış zamanı", ColumnKind.DATETIME),
            Column("sale_no", "Belge"),
            Column("channel", "Kanal", ColumnKind.STATUS),
            Column("customer", "Müşteri"),
            Column("product", "Ürün"),
            Column("lot_no", "Lot"),
            Column("qty", "Miktar", ColumnKind.QTY),
            Column("unit", "Birim"),
            Column("unit_price", "Birim fiyat", ColumnKind.MONEY),
            Column("amount", "Tutar", ColumnKind.MONEY),
            Column("cost", "Maliyet", ColumnKind.MONEY),
            Column("gross_profit", "Brüt kâr", ColumnKind.MONEY),
            Column("margin_pct", "Marj %", ColumnKind.PERCENT),
            Column("returned_qty", "İade", ColumnKind.QTY),
            Column("recall_violation", "Geri çağırma ihlali", ColumnKind.BOOL),
        ],
        rows=rows,
        totals={key: _total(rows, key) for key in ("amount", "cost", "gross_profit")},
    )


# --- FR-606 Geri çağırma ---


def _recalls(session: Session, f: ReportFilter) -> Report:
    query = select(Recall).where(*_day_range(Recall.started_at, f)).order_by(Recall.id)
    rows = []
    for recall in session.scalars(query):
        view = recall_view(session, recall)
        if f.lot_no and not any(f.lot_no in lot.lot_no for lot in view.lots):
            continue
        common = {
            "recall_no": recall.recall_no,
            "started_at": recall.started_at,
            "status": recall.status,
            "resolution": recall.resolution,
            "source_lot_no": view.source_lot_no,
            "reason": recall.reason,
            "affected_lots": ", ".join(lot.lot_no for lot in view.lots),
        }
        if not view.recipients:
            rows.append({**common, "customer": None, "lot_no": None, "qty": None, "unit": None})
        for r in view.recipients:
            rows.append(
                {
                    **common,
                    "customer": r.customer,
                    "phone": r.contact.phone,
                    "lot_no": r.lot_no,
                    "qty": r.qty,
                    "unit": _unit(r.base_unit),
                    "sales": ", ".join(s.sale_no for s in r.sales),
                    "onward": r.onward_status,
                    "recall_violation": r.recall_violation,
                }
            )
    return Report(
        code=ReportCode.RECALLS,
        title=META[ReportCode.RECALLS][0],
        description=META[ReportCode.RECALLS][1],
        columns=[
            Column("recall_no", "Geri çağırma"),
            Column("started_at", "Başlangıç", ColumnKind.DATETIME),
            Column("status", "Durum", ColumnKind.STATUS),
            Column("resolution", "Sonuç", ColumnKind.STATUS),
            Column("source_lot_no", "Kaynak lot"),
            Column("reason", "Neden"),
            Column("affected_lots", "Etkilenen lotlar"),
            Column("customer", "Alıcı"),
            Column("phone", "Telefon"),
            Column("lot_no", "Lot"),
            Column("qty", "Müşteride kalan", ColumnKind.QTY),
            Column("unit", "Birim"),
            Column("sales", "Satış belgeleri"),
            Column("onward", "İkinci kademe", ColumnKind.STATUS),
            Column("recall_violation", "Çevrimdışı ihlal", ColumnKind.BOOL),
        ],
        rows=rows,
    )


# --- FR-607 Bütünlük ---


def _integrity(session: Session, f: ReportFilter) -> Report:
    results = check_invariants(session)
    rows = [
        {
            "code": r.code,
            "description": r.description,
            "ok": r.ok,
            "violation_count": len(r.violations),
            "examples": "; ".join(r.violations[:3]),
        }
        for r in results
    ]
    passed = sum(1 for r in results if r.ok)
    return Report(
        code=ReportCode.INTEGRITY,
        title=META[ReportCode.INTEGRITY][0],
        description=META[ReportCode.INTEGRITY][1],
        columns=[
            Column("code", "Kural"),
            Column("description", "Açıklama"),
            Column("ok", "Tutarlı", ColumnKind.BOOL),
            Column("violation_count", "İhlal sayısı", ColumnKind.QTY),
            Column("examples", "Örnekler"),
        ],
        rows=rows,
        notes=[f"{passed}/{len(results)} kural tutarlı."],
    )


_BUILDERS: dict[ReportCode, Callable[[Session, ReportFilter], Report]] = {
    ReportCode.PURCHASES: _purchases,
    ReportCode.PRODUCTION: _production,
    ReportCode.CUTTINGS: _cuttings,
    ReportCode.LOT_MOVEMENTS: _lot_movements,
    ReportCode.SALES: _sales,
    ReportCode.RECALLS: _recalls,
    ReportCode.INTEGRITY: _integrity,
}

# Raporun desteklediği süzgeçler (web ekranı yalnız bunları gösterir).
FILTERS: dict[ReportCode, tuple[str, ...]] = {
    ReportCode.PURCHASES: ("date", "product", "lot"),
    ReportCode.PRODUCTION: ("date", "product", "lot"),
    ReportCode.CUTTINGS: ("date", "product", "lot"),
    ReportCode.LOT_MOVEMENTS: ("date", "product", "lot"),
    ReportCode.SALES: ("date", "product", "lot"),
    ReportCode.RECALLS: ("date", "lot"),
    ReportCode.INTEGRITY: (),
}
