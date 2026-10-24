"""Android senkronizasyonu — sunucudan cihaza çekme (ADR-004, architecture.md §5).

Cihaz son aldığı değişiklik numarasını (since) gönderir; yalnız ondan sonra değişen kayıtlar döner.
Sayaç ve kayıtlar aynı işlemde okunduğu için (InnoDB tutarlı okuma) dönen next_since güvenlidir.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.orm import Session

from app.errors import Forbidden
from app.models import Lot, Partner, Product, StockBalance, User
from app.models.sync import SyncCounter


@dataclass(frozen=True)
class PullResult:
    next_since: int
    products: list[Product]
    customers: list[Partner]
    lots: list[Lot]
    stock: list[StockBalance]


def pull_changes(session: Session, user: User, since: int) -> PullResult:
    if user.warehouse_id is None:
        raise Forbidden("Bu kullanıcıya araç deposu atanmamış; senkronizasyon yapılamaz.")
    upto = session.scalar(select(SyncCounter.value).where(SyncCounter.id == 1)) or 0

    def changed(column: Any) -> ColumnElement[bool]:
        return and_(column > since, column <= upto)

    warehouse = user.warehouse_id
    products = session.scalars(select(Product).where(changed(Product.change_seq)).order_by(Product.id)).all()
    customers = session.scalars(
        select(Partner).where(Partner.is_customer, changed(Partner.change_seq)).order_by(Partner.id)
    ).all()
    stock = session.scalars(
        select(StockBalance)
        .where(StockBalance.warehouse_id == warehouse, changed(StockBalance.change_seq))
        .order_by(StockBalance.lot_id)
    ).all()
    # Araç deposunda bakiyesi olan lotlar: lot (ör. bloke edildi) ya da bakiyesi değiştiyse.
    lots = session.scalars(
        select(Lot)
        .join(StockBalance, and_(StockBalance.lot_id == Lot.id, StockBalance.warehouse_id == warehouse))
        .where(or_(changed(Lot.change_seq), changed(StockBalance.change_seq)))
        .order_by(Lot.id)
    ).all()
    return PullResult(
        next_since=upto,
        products=list(products),
        customers=list(customers),
        lots=list(lots),
        stock=list(stock),
    )
