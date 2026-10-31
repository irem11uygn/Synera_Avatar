"""Satış — Android'den gelen satışların sunucuya yazılması (FR-401, FR-403, FR-405; ADR-004).

Her satış cihazda üretilen UUID ile gelir; aynı UUID ikinci kez gelirse yeni kayıt açılmaz, ilk
sonuç döner (tekrar güvenlik, AT-11). Her satış kendi alt işleminde (savepoint) yazılır: biri
reddedilirse yalnız o geri alınır, aynı gönderimdeki diğerleri kaydedilir.

Bir satır = bir lot = bir stok hareketi; satırın maliyeti hareketin lot değerinden gelir.
Çevrimdışıyken geri çağrılmış (bloke) bir lot satıldıysa satış kaydedilir, ihlal işaretlenir ve
yöneticiye uyarı düşer — mal müşteriye gitmiştir, kaydı reddetmek izini kaybettirir (ADR-004).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.clock import business_today
from app.domain.costing import line_amount
from app.domain.money import tr_number
from app.errors import DomainError, Forbidden, InvalidInput, NotFound
from app.models import Lot, Partner, Product, Sale, SaleLine, User
from app.models.enums import (
    AlertKind,
    BaseUnit,
    DocType,
    LotStatus,
    MovementType,
    PaymentMethod,
    SaleChannel,
    Severity,
    WarehouseKind,
)
from app.models.types import utcnow
from app.services import audit
from app.services.alarms import raise_alarm
from app.services.ledger import post_movement
from app.services.lookups import warehouse_or_404
from app.services.numbering import next_document_no


class PushStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    ACCEPTED_WITH_WARNING = "ACCEPTED_WITH_WARNING"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class SaleLineInput:
    lot_no: str
    qty: Decimal
    unit_price: Decimal


@dataclass(frozen=True)
class SaleInput:
    client_uuid: str
    customer_id: int
    warehouse_id: int
    sold_at: datetime
    lines: Sequence[SaleLineInput]
    payment_method: PaymentMethod | None = None


@dataclass(frozen=True)
class PushResult:
    client_uuid: str
    status: PushStatus
    sale_no: str | None = None
    warnings: list[str] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


def push_sales(
    session: Session, user: User, device_id: str | None, sales: Sequence[SaleInput]
) -> list[PushResult]:
    if user.warehouse_id is None:
        raise Forbidden("Bu kullanıcıya araç deposu atanmamış; satış gönderilemez.")
    if any(sale.warehouse_id != user.warehouse_id for sale in sales):
        raise Forbidden("Satışlar yalnız kullanıcının kendi araç deposundan gönderilebilir.")
    return [_push_one(session, user, device_id, sale) for sale in sales]


def _push_one(session: Session, user: User, device_id: str | None, sale: SaleInput) -> PushResult:
    existing = session.scalars(select(Sale).where(Sale.client_uuid == sale.client_uuid)).first()
    if existing is not None:
        return PushResult(
            client_uuid=sale.client_uuid,
            status=PushStatus.DUPLICATE,
            sale_no=existing.sale_no,
            warnings=_warnings(session, existing),
        )
    try:
        with session.begin_nested():
            saved = _record_sale(session, user, device_id, sale)
    except DomainError as error:
        return PushResult(
            client_uuid=sale.client_uuid,
            status=PushStatus.REJECTED,
            error_code=error.code,
            error_message=error.message,
        )
    warnings = _warnings(session, saved)
    return PushResult(
        client_uuid=sale.client_uuid,
        status=PushStatus.ACCEPTED_WITH_WARNING if warnings else PushStatus.ACCEPTED,
        sale_no=saved.sale_no,
        warnings=warnings,
    )


def _record_sale(
    session: Session,
    user: User,
    device_id: str | None,
    data: SaleInput,
    *,
    channel: SaleChannel = SaleChannel.ANDROID,
) -> Sale:
    """Satışı deftere yazar. Android (çevrimdışı olabilir): bloke ya da SKT'si geçmiş parti kayda alınır,
    ihlal işaretlenir, uyarı düşer — mal müşteriye gitmiştir. Mağaza (web, anlık): bu partiler reddedilir."""
    offline = channel == SaleChannel.ANDROID
    customer = session.get(Partner, data.customer_id)
    if customer is None or not customer.is_customer:
        raise InvalidInput(
            "Müşteri bulunamadı veya müşteri olarak tanımlı değil.", customer_id=data.customer_id
        )
    if not data.lines:
        raise InvalidInput("Satışta en az bir satır olmalı.")
    sold_at = data.sold_at.astimezone(UTC).replace(tzinfo=None) if data.sold_at.tzinfo else data.sold_at
    sale_day = business_today(sold_at)
    lots = [_sellable_lot(session, line, sale_day=sale_day, offline=offline) for line in data.lines]

    sale = Sale(
        client_uuid=data.client_uuid,
        sale_no=next_document_no(session, "SAT", utcnow().year),
        channel=channel,
        customer_id=customer.id,
        warehouse_id=data.warehouse_id,
        user_id=user.id,
        device_id=device_id,
        sold_at=sold_at,
        recall_violation=any(lot.status == LotStatus.BLOKE for lot in lots),
        payment_method=data.payment_method,
    )
    session.add(sale)
    session.flush()
    below_list: list[str] = []
    for line_no, (line, lot) in enumerate(zip(data.lines, lots, strict=True), start=1):
        movement = post_movement(
            session,
            lot_id=lot.id,
            warehouse_id=data.warehouse_id,
            movement_type=MovementType.SATIS,
            qty=-line.qty,
            doc_type=DocType.SATIS,
            doc_id=sale.id,
            user_id=user.id,
            allow_blocked=offline,  # çevrimdışı satış kaydedilir, ihlal aşağıda işaretlenir
        )
        session.add(
            SaleLine(
                sale_id=sale.id,
                line_no=line_no,
                product_id=lot.product_id,
                lot_id=lot.id,
                qty=line.qty,
                unit_price=line.unit_price,
                amount=line_amount(line.qty, line.unit_price),
                stock_movement_id=movement.id,
                cost_amount=-movement.value,
            )
        )
        product = session.get(Product, lot.product_id)
        unit = "adet" if product is not None and product.base_unit == BaseUnit.ADET else "kg"
        if product is not None and _below_list(line.unit_price, product.sale_price):
            list_price = product.sale_price
            pct = _discount_pct(line.unit_price, list_price).quantize(Decimal("0.1"))
            below_list.append(
                f"{lot.lot_no} {tr_number(line.unit_price, 2)} € "
                f"(liste {tr_number(list_price, 2)} €, %{tr_number(pct)} altında)"
            )
        if lot.status == LotStatus.BLOKE:
            raise_alarm(
                session,
                AlertKind.GERI_CAGIRMA_IHLALI,
                Severity.KRITIK,
                f"{sale.sale_no}: bloke {lot.lot_no} lotundan {tr_number(line.qty)} {unit} "
                f"{customer.name} müşterisine satıldı (çevrimdışı satış). Müşteriyi geri çağırma "
                "listesine ekleyin.",
                ref_type="SALE",
                ref_id=sale.id,
                user=user,
            )
        if _expired(lot, sale_day):
            raise_alarm(
                session,
                AlertKind.SKT_IHLALI,
                Severity.UYARI,
                f"{sale.sale_no}: son kullanma tarihi geçmiş {lot.lot_no} partisinden "
                f"{tr_number(line.qty)} {unit} {customer.name} müşterisine satıldı "
                "(çevrimdışı satış). Müşteriyle iletişime geçin.",
                ref_type="SALE",
                ref_id=sale.id,
                user=user,
            )
    if below_list:
        # Satış engellenmez (indirim satıcının işi olabilir) ama yönetici denetim günlüğünde görür.
        audit.log(
            session,
            "LISTE_ALTI_FIYAT",
            f"{sale.sale_no} ({customer.name}): liste fiyatının altında satış — {'; '.join(below_list)}",
            user=user,
            severity=Severity.UYARI,
            ref_type="SALE",
            ref_id=sale.id,
        )
    session.flush()
    return sale


def _below_list(unit_price: Decimal, list_price: Decimal | None) -> bool:
    return list_price is not None and list_price > 0 and unit_price < list_price


def _discount_pct(unit_price: Decimal, list_price: Decimal) -> Decimal:
    return (list_price - unit_price) / list_price * 100


@dataclass(frozen=True)
class StoreLineInput:
    lot_no: str
    qty: Decimal
    unit_price: Decimal | None = None  # boşsa ürünün liste fiyatı


def create_store_sale(
    session: Session,
    user: User,
    *,
    customer_id: int,
    warehouse_id: int,
    lines: Sequence[StoreLineInput],
    payment_method: PaymentMethod,
) -> Sale:
    """Mağaza (web) satışı: anlık kayıt; bloke ya da SKT'si geçmiş parti satılamaz. Araç stoku
    telefondan satılır; fasoncu deposu satış yeri değildir."""
    warehouse = warehouse_or_404(session, warehouse_id)
    if warehouse.kind != WarehouseKind.ANA:
        raise InvalidInput("Mağaza satışı yalnız ana depodan yapılır; araç stoku telefondan satılır.")
    data = SaleInput(
        client_uuid=str(uuid4()),
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        sold_at=utcnow(),
        lines=[SaleLineInput(line.lot_no, line.qty, _list_price(session, line)) for line in lines],
        payment_method=payment_method,
    )
    return _record_sale(session, user, None, data, channel=SaleChannel.WEB)


def _list_price(session: Session, line: StoreLineInput) -> Decimal:
    if line.unit_price is not None:
        return line.unit_price
    lot = session.scalars(select(Lot).where(Lot.lot_no == line.lot_no)).first()
    if lot is None:
        raise NotFound(f"{line.lot_no} lotu bulunamadı.", lot_no=line.lot_no)
    product = session.get(Product, lot.product_id)
    if product is None or product.sale_price is None:
        raise InvalidInput(f"{line.lot_no}: ürünün satış fiyatı tanımlı değil; fiyatı elle yazın.")
    return product.sale_price


def _expired(lot: Lot, day: date) -> bool:
    return lot.expiry_date is not None and lot.expiry_date < day


def _sellable_lot(session: Session, line: SaleLineInput, *, sale_day: date, offline: bool) -> Lot:
    lot = session.scalars(select(Lot).where(Lot.lot_no == line.lot_no)).first()
    if lot is None:
        raise NotFound(f"{line.lot_no} lotu bulunamadı.", lot_no=line.lot_no)
    product = session.get(Product, lot.product_id)
    assert product is not None
    if line.qty <= 0:
        raise InvalidInput(f"{lot.lot_no}: satış miktarı sıfırdan büyük olmalı.")
    if line.unit_price < 0:
        raise InvalidInput(f"{lot.lot_no}: birim fiyat eksi olamaz.")
    if product.base_unit == BaseUnit.ADET and line.qty != line.qty.to_integral_value():
        raise InvalidInput(f"{product.name} adet ile satılır; {tr_number(line.qty)} adet olamaz.")
    if not offline and _expired(lot, sale_day):
        raise InvalidInput(
            f"{lot.lot_no} partisinin son kullanma tarihi geçmiş ({lot.expiry_date:%d.%m.%Y}); satılamaz.",
            lot_no=lot.lot_no,
        )
    return lot


def _warnings(session: Session, sale: Sale) -> list[str]:
    rows = session.execute(
        select(Lot.lot_no, Lot.status, Lot.expiry_date, SaleLine.unit_price, Product.sale_price)
        .join(SaleLine, SaleLine.lot_id == Lot.id)
        .join(Product, Product.id == SaleLine.product_id)
        .where(SaleLine.sale_id == sale.id)
        .order_by(SaleLine.line_no)
    ).all()
    sale_day = business_today(sale.sold_at)
    warnings = []
    if sale.recall_violation:
        blocked = ", ".join(no for no, status, *_ in rows if status == LotStatus.BLOKE) or "bloke lot"
        warnings.append(
            f"Geri çağrılmış lot satıldı ({blocked}); satış kaydedildi, ihlal yöneticiye bildirildi."
        )
    expired = [no for no, _, expiry, *_ in rows if expiry is not None and expiry < sale_day]
    if expired:
        warnings.append(
            f"Son kullanma tarihi geçmiş parti satıldı ({', '.join(expired)}); "
            "satış kaydedildi, yöneticiye bildirildi."
        )
    below = [no for no, _, _, price, list_price in rows if _below_list(price, list_price)]
    if below:
        warnings.append(f"Liste fiyatının altında satış ({', '.join(below)}); yöneticiye bildirildi.")
    return warnings


# --- Okuma modeli ---


@dataclass(frozen=True)
class SaleLineView:
    id: int
    line_no: int
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    qty: Decimal
    unit_price: Decimal
    amount: Decimal
    cost_amount: Decimal


@dataclass(frozen=True)
class SaleView:
    sale: Sale
    customer_name: str
    seller_name: str
    lines: list[SaleLineView]
    total_amount: Decimal
    total_cost: Decimal


def sale_view(session: Session, sale: Sale) -> SaleView:
    customer = session.get(Partner, sale.customer_id)
    seller = session.get(User, sale.user_id) if sale.user_id is not None else None
    rows = session.execute(
        select(SaleLine, Lot.lot_no, Product.name, Product.base_unit)
        .join(Lot, Lot.id == SaleLine.lot_id)
        .join(Product, Product.id == SaleLine.product_id)
        .where(SaleLine.sale_id == sale.id)
        .order_by(SaleLine.line_no)
    ).all()
    lines = [
        SaleLineView(
            id=line.id,
            line_no=line.line_no,
            lot_no=lot_no,
            product_name=name,
            base_unit=unit,
            qty=line.qty,
            unit_price=line.unit_price,
            amount=line.amount,
            cost_amount=line.cost_amount,
        )
        for line, lot_no, name, unit in rows
    ]
    return SaleView(
        sale=sale,
        customer_name=customer.name if customer else "",
        seller_name=seller.full_name if seller else "",
        lines=lines,
        total_amount=sum((line.amount for line in lines), Decimal("0.00")),
        total_cost=sum((line.cost_amount for line in lines), Decimal("0.00")),
    )
