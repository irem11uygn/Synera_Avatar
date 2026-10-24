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
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.costing import line_amount
from app.domain.money import tr_number
from app.errors import DomainError, Forbidden, InvalidInput, NotFound
from app.models import Alert, Lot, Partner, Product, Sale, SaleLine, User
from app.models.enums import AlertKind, BaseUnit, DocType, LotStatus, MovementType, SaleChannel
from app.models.types import utcnow
from app.services.ledger import post_movement
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


def _record_sale(session: Session, user: User, device_id: str | None, data: SaleInput) -> Sale:
    customer = session.get(Partner, data.customer_id)
    if customer is None or not customer.is_customer:
        raise InvalidInput(
            "Müşteri bulunamadı veya müşteri olarak tanımlı değil.", customer_id=data.customer_id
        )
    if not data.lines:
        raise InvalidInput("Satışta en az bir satır olmalı.")
    lots = [_sellable_lot(session, line) for line in data.lines]

    sale = Sale(
        client_uuid=data.client_uuid,
        sale_no=next_document_no(session, "SAT", utcnow().year),
        channel=SaleChannel.ANDROID,
        customer_id=customer.id,
        warehouse_id=data.warehouse_id,
        user_id=user.id,
        device_id=device_id,
        sold_at=data.sold_at.astimezone(UTC).replace(tzinfo=None) if data.sold_at.tzinfo else data.sold_at,
        recall_violation=any(lot.status == LotStatus.BLOKE for lot in lots),
    )
    session.add(sale)
    session.flush()
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
            allow_blocked=True,  # çevrimdışı satış kaydedilir, ihlal aşağıda işaretlenir
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
        if lot.status == LotStatus.BLOKE:
            session.add(
                Alert(
                    kind=AlertKind.GERI_CAGIRMA_IHLALI,
                    ref_type="SALE",
                    ref_id=sale.id,
                    message=(
                        f"{sale.sale_no}: bloke {lot.lot_no} lotundan {tr_number(line.qty)} birim "
                        f"{customer.name} müşterisine satıldı (çevrimdışı satış). Müşteriyi geri çağırma "
                        "listesine ekleyin."
                    ),
                )
            )
    session.flush()
    return sale


def _sellable_lot(session: Session, line: SaleLineInput) -> Lot:
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
    return lot


def _warnings(session: Session, sale: Sale) -> list[str]:
    if not sale.recall_violation:
        return []
    blocked = session.scalars(
        select(Lot.lot_no)
        .join(SaleLine, SaleLine.lot_id == Lot.id)
        .where(SaleLine.sale_id == sale.id, Lot.status == LotStatus.BLOKE)
        .order_by(SaleLine.line_no)
    ).all()
    lots = ", ".join(blocked) or "bloke lot"
    return [f"Geri çağrılmış lot satıldı ({lots}); satış kaydedildi, ihlal yöneticiye bildirildi."]


# --- Okuma modeli ---


@dataclass(frozen=True)
class SaleLineView:
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
    lines: list[SaleLineView]
    total_amount: Decimal
    total_cost: Decimal


def sale_view(session: Session, sale: Sale) -> SaleView:
    customer = session.get(Partner, sale.customer_id)
    rows = session.execute(
        select(SaleLine, Lot.lot_no, Product.name, Product.base_unit)
        .join(Lot, Lot.id == SaleLine.lot_id)
        .join(Product, Product.id == SaleLine.product_id)
        .where(SaleLine.sale_id == sale.id)
        .order_by(SaleLine.line_no)
    ).all()
    lines = [
        SaleLineView(
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
        lines=lines,
        total_amount=sum((line.amount for line in lines), Decimal("0.00")),
        total_cost=sum((line.cost_amount for line in lines), Decimal("0.00")),
    )
