"""Stok hareket defteri — deftere yazmanın TEK yolu (ADR-008, architecture.md §3.1–3.2).

Her hareket: lot, ürün ve depo zorunlu; bloke ve eksi stok denetimi; değerleme kuralı;
lot özeti ve depo bakiyesi aynı işlemde güncellenir. Kilit sırası: önce lot, sonra bakiye.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.costing import outflow_value, unit_cost
from app.errors import DuplicateLotNo, InsufficientStock, InvalidInput, LotBlocked, NotFound
from app.models import Lot, StockBalance, StockMovement
from app.models.enums import DocType, LotOrigin, LotStatus, MovementType

_SIGN = {
    MovementType.ALIS_GIRIS: 1,
    MovementType.TRANSFER_CIKIS: -1,
    MovementType.TRANSFER_GIRIS: 1,
    MovementType.URETIM_TUKETIM: -1,
    MovementType.URETIM_GIRIS: 1,
    MovementType.PARCALAMA_TUKETIM: -1,
    MovementType.PARCALAMA_GIRIS: 1,
    MovementType.SATIS: -1,
    MovementType.IADE_GIRIS: 1,
    MovementType.FIRE: -1,
}  # TERS_KAYIT: aslının tersi, işaret serbest
LOT_CREATING = {MovementType.ALIS_GIRIS, MovementType.URETIM_GIRIS, MovementType.PARCALAMA_GIRIS}
VALUED_OUTFLOWS = {
    MovementType.URETIM_TUKETIM,
    MovementType.PARCALAMA_TUKETIM,
    MovementType.SATIS,
    MovementType.FIRE,
}
TRANSFERS = {MovementType.TRANSFER_CIKIS, MovementType.TRANSFER_GIRIS}
ALLOWED_ON_BLOCKED = {MovementType.IADE_GIRIS, MovementType.FIRE, MovementType.TERS_KAYIT}


def create_lot(
    session: Session,
    *,
    lot_no: str,
    product_id: int,
    origin: LotOrigin,
    qty: Decimal,
    value: Decimal,
    warehouse_id: int,
    movement_type: MovementType,
    doc_type: DocType,
    doc_id: int,
    supplier_id: int | None = None,
    produced_at: date | None = None,
    expiry_date: date | None = None,
    user_id: int | None = None,
) -> Lot:
    """Yeni lot açar ve onu oluşturan giriş hareketini yazar (alış, üretim, parçalama)."""
    if movement_type not in LOT_CREATING:
        raise InvalidInput("Lot yalnız alış, üretim veya parçalama girişiyle açılabilir.", type=movement_type)
    if qty <= 0 or value < 0:
        raise InvalidInput("Lot miktarı pozitif, değeri sıfır veya pozitif olmalı.", qty=qty, value=value)
    if session.scalar(select(Lot.id).where(Lot.lot_no == lot_no)) is not None:
        raise DuplicateLotNo(f"{lot_no} lot numarası zaten kayıtlı.", lot_no=lot_no)

    lot = Lot(
        lot_no=lot_no,
        product_id=product_id,
        origin=origin,
        supplier_id=supplier_id,
        produced_at=produced_at,
        expiry_date=expiry_date,
        status=LotStatus.AKTIF,
        initial_qty=qty,
        initial_value=value,
        unit_cost=unit_cost(value, qty),
        remaining_qty=Decimal(0),
        remaining_value=Decimal(0),
        created_by=user_id,
    )
    session.add(lot)
    session.flush()
    post_movement(
        session,
        lot_id=lot.id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        qty=qty,
        value=value,
        doc_type=doc_type,
        doc_id=doc_id,
        user_id=user_id,
    )
    return lot


def post_movement(
    session: Session,
    *,
    lot_id: int,
    warehouse_id: int,
    movement_type: MovementType,
    qty: Decimal,
    doc_type: DocType,
    doc_id: int,
    value: Decimal | None = None,
    user_id: int | None = None,
    note: str | None = None,
    allow_blocked: bool = False,
    reversal_of_id: int | None = None,
) -> StockMovement:
    """Deftere bir hareket yazar ve özetleri günceller.

    value: değerli çıkışlarda (tüketim, satış, fire) ve transferlerde hesaplanır, verilmez;
    girişlerde ve ters kayıtta çağıran verir. allow_blocked: yalnız çevrimdışı yapılmış
    Android satışının kaydı için (ADR-004 — satış kaydedilir, ihlal işaretlenir).
    """
    _check_sign(movement_type, qty)
    lot = _lock_lot(session, lot_id)
    balance = _lock_balance(session, lot_id, warehouse_id)

    if lot.status == LotStatus.BLOKE and movement_type not in ALLOWED_ON_BLOCKED and not allow_blocked:
        raise LotBlocked(
            f"{lot.lot_no} lotu geri çağırma nedeniyle bloke; bu işlem yapılamaz.", lot_no=lot.lot_no
        )
    if qty < 0 and balance.qty + qty < 0:
        raise InsufficientStock(
            f"{lot.lot_no} lotunda bu depoda yeterli stok yok.",
            lot_no=lot.lot_no,
            available=balance.qty,
            requested=-qty,
        )

    movement_value = _movement_value(lot, movement_type, qty, value)
    lot.remaining_qty += qty
    lot.remaining_value += movement_value
    balance.qty += qty
    movement = StockMovement(
        type=movement_type,
        lot_id=lot.id,
        product_id=lot.product_id,
        warehouse_id=warehouse_id,
        qty=qty,
        value=movement_value,
        doc_type=doc_type,
        doc_id=doc_id,
        user_id=user_id,
        note=note,
        reversal_of_id=reversal_of_id,
    )
    session.add(movement)
    session.flush()
    return movement


def post_transfer(
    session: Session,
    *,
    lot_id: int,
    from_warehouse_id: int,
    to_warehouse_id: int,
    qty: Decimal,
    doc_id: int,
    user_id: int | None = None,
) -> tuple[StockMovement, StockMovement]:
    """Depolar arası transfer: çıkış ve giriş hareketi; lot değeri değişmez (değer 0)."""
    if from_warehouse_id == to_warehouse_id:
        raise InvalidInput("Transferde çıkış ve giriş deposu farklı olmalı.")
    if qty <= 0:
        raise InvalidInput("Transfer miktarı sıfırdan büyük olmalı.", qty=qty)
    common = {"lot_id": lot_id, "doc_type": DocType.TRANSFER, "doc_id": doc_id, "user_id": user_id}
    out = post_movement(
        session, warehouse_id=from_warehouse_id, movement_type=MovementType.TRANSFER_CIKIS, qty=-qty, **common
    )
    into = post_movement(
        session, warehouse_id=to_warehouse_id, movement_type=MovementType.TRANSFER_GIRIS, qty=qty, **common
    )
    return out, into


def reverse_movement(
    session: Session, movement_id: int, reason: str, user_id: int | None = None
) -> StockMovement:
    """Hatalı hareketi ters kayıtla düzeltir: miktar ve değer aslının tam tersi (NFR-002)."""
    original = session.get(StockMovement, movement_id)
    if original is None:
        raise NotFound("Hareket bulunamadı.", movement_id=movement_id)
    if not reason.strip():
        raise InvalidInput("Ters kayıt için gerekçe zorunlu.")
    if original.type == MovementType.TERS_KAYIT:
        raise InvalidInput("Ters kaydın kendisi ters çevrilemez.", movement_id=movement_id)
    if session.scalar(select(StockMovement.id).where(StockMovement.reversal_of_id == movement_id)):
        raise InvalidInput("Bu hareket zaten ters kayıtla düzeltilmiş.", movement_id=movement_id)
    return post_movement(
        session,
        lot_id=original.lot_id,
        warehouse_id=original.warehouse_id,
        movement_type=MovementType.TERS_KAYIT,
        qty=-original.qty,
        value=-original.value,
        doc_type=original.doc_type,
        doc_id=original.doc_id,
        user_id=user_id,
        note=reason,
        reversal_of_id=original.id,
    )


def _check_sign(movement_type: MovementType, qty: Decimal) -> None:
    if qty == 0:
        raise InvalidInput("Hareket miktarı sıfır olamaz.")
    expected = _SIGN.get(movement_type)
    if expected is not None and (qty > 0) != (expected > 0):
        direction = "pozitif (giriş)" if expected > 0 else "negatif (çıkış)"
        raise InvalidInput(f"{movement_type} hareketinin miktarı {direction} olmalı.", qty=qty)


def _movement_value(lot: Lot, movement_type: MovementType, qty: Decimal, value: Decimal | None) -> Decimal:
    if movement_type in TRANSFERS:
        if value not in (None, Decimal(0)):
            raise InvalidInput("Transfer hareketi değer taşımaz.")
        return Decimal(0)
    if movement_type in VALUED_OUTFLOWS:
        if value is not None:
            raise InvalidInput("Çıkış hareketinin değeri defterde hesaplanır, dışarıdan verilmez.")
        return -outflow_value(lot.remaining_qty, lot.remaining_value, -qty)
    if value is None:
        raise InvalidInput(f"{movement_type} hareketi için değer verilmeli.")
    return value


def _lock_lot(session: Session, lot_id: int) -> Lot:
    lot = session.execute(
        select(Lot).where(Lot.id == lot_id).with_for_update().execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if lot is None:
        raise NotFound("Lot bulunamadı.", lot_id=lot_id)
    return lot


def _lock_balance(session: Session, lot_id: int, warehouse_id: int) -> StockBalance:
    balance = session.execute(
        select(StockBalance)
        .where(StockBalance.lot_id == lot_id, StockBalance.warehouse_id == warehouse_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if balance is None:
        balance = StockBalance(lot_id=lot_id, warehouse_id=warehouse_id, qty=Decimal(0))
        session.add(balance)
        session.flush()
    return balance
