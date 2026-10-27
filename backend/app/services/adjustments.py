"""Stok firesi/imhası ve hatalı hareketin ters kaydı (FR-303, NFR-002).

Fire: depodaki malın bozulması, kaybı ya da imhası; lot değeri ortalama birim maliyetle düşer.
Bloke lotta da yapılabilir (geri çağrılan malın imhası).

Ters kayıt: defterde hiçbir hareket silinmez ya da değiştirilmez; hata, aslının tam tersi olan yeni
bir hareketle düzeltilir. Yalnız kendi başına duran belgelerin hareketleri ters çevrilebilir: fire,
iade ve elle yapılan transfer (iki hareketi birlikte). Üretim, parçalama ve satış hareketleri başka
kayıtlara (lot bağları, maliyet, satış satırı) bağlı olduğu için ters kayıtla değil, kendi
belgesiyle düzeltilir (iptal, iade).
"""

from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.errors import InvalidInput, InvalidState
from app.models import Adjustment, StockMovement, Transfer, TransferLine
from app.models.enums import AdjustmentKind, DocType, MovementType
from app.models.types import utcnow
from app.services.ledger import post_movement, reverse_movement
from app.services.lookups import get_or_404, warehouse_or_404
from app.services.numbering import next_document_no

REVERSIBLE = {MovementType.FIRE, MovementType.IADE_GIRIS}
TRANSFER_TYPES = {MovementType.TRANSFER_CIKIS, MovementType.TRANSFER_GIRIS}


def create_adjustment(
    session: Session,
    *,
    lot_id: int,
    warehouse_id: int,
    qty: Decimal,
    reason: str,
    user_id: int | None = None,
) -> Adjustment:
    if qty <= 0:
        raise InvalidInput("Fire miktarı sıfırdan büyük olmalı.")
    if not reason.strip():
        raise InvalidInput("Fire/imha için gerekçe zorunlu.")
    warehouse_or_404(session, warehouse_id)
    record = Adjustment(
        adj_no=next_document_no(session, "FIR", utcnow().year),
        kind=AdjustmentKind.FIRE,
        lot_id=lot_id,
        warehouse_id=warehouse_id,
        qty=qty,
        reason=reason.strip(),
        created_by=user_id,
    )
    session.add(record)
    session.flush()
    movement = post_movement(
        session,
        lot_id=lot_id,
        warehouse_id=warehouse_id,
        movement_type=MovementType.FIRE,
        qty=-qty,
        doc_type=DocType.DUZELTME,
        doc_id=record.id,
        user_id=user_id,
        note=record.reason,
    )
    record.stock_movement_id = movement.id
    session.flush()
    return record


def reverse(
    session: Session, movement_id: int, reason: str, user_id: int | None = None
) -> list[StockMovement]:
    """Hareketi (transferde iki hareketi birlikte) ters kayıtla düzeltir; yazılan ters kayıtları döner."""
    movement = get_or_404(session, StockMovement, movement_id, "Hareket")
    if movement.type in REVERSIBLE:
        return [reverse_movement(session, movement.id, reason, user_id)]
    if movement.type in TRANSFER_TYPES:
        line = session.scalars(
            select(TransferLine).where(
                or_(TransferLine.out_movement_id == movement.id, TransferLine.in_movement_id == movement.id)
            )
        ).one()
        transfer = session.get(Transfer, line.transfer_id)
        assert transfer is not None
        if transfer.production_order_id is not None:
            raise InvalidState(
                "Dış üretim sevkiyatı/iadesi ters kayıtla değil, üretim emri üzerinden düzeltilir.",
                transfer_no=transfer.transfer_no,
            )
        # Önce giriş geri alınır (varış deposunda mal hâlâ duruyor mu denetlenir), sonra çıkış.
        return [
            reverse_movement(session, line.in_movement_id, reason, user_id),
            reverse_movement(session, line.out_movement_id, reason, user_id),
        ]
    raise InvalidState(
        f"{movement.type} hareketi ters kayıtla düzeltilemez; kendi belgesinden (iptal, iade) düzeltilir.",
        movement_id=movement.id,
        type=movement.type,
    )
