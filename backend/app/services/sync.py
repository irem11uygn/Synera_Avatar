"""Android senkronizasyonu — sunucudan cihaza çekme (ADR-004, architecture.md §5).

Cihaz son aldığı değişiklik numarasını (since) gönderir; yalnız ondan sonra değişen kayıtlar döner.
Yanıttaki veri kümesi kimliği (dataset_id) değişmişse ya da next_since cihazın since değerinden küçükse
(sunucu sıfırlandı ya da eski bir yedekten döndü) cihaz yerel kopyasını silip since=0 ile baştan çeker.
Kayıtlar since < change_seq ≤ upto aralığıyla süzülür. Sayaç satır kilidi numaraları işlenme sırasıyla
dağıttığı için upto'ya kadarki bütün değişiklikler kaydedilmiştir; sayaç okunduktan sonra kaydedilenler
bir sonraki çekişe kalır. Bu yüzden READ COMMITTED yalıtımında da (her sorgu yeni anlık görüntü)
kayıt atlanmaz.
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
    dataset_id: str
    next_since: int
    products: list[Product]
    customers: list[Partner]
    lots: list[Lot]
    stock: list[StockBalance]


def pull_changes(session: Session, user: User, since: int) -> PullResult:
    if user.warehouse_id is None:
        raise Forbidden("Bu kullanıcıya araç deposu atanmamış; senkronizasyon yapılamaz.")
    dataset_id, upto = session.execute(
        select(SyncCounter.dataset_id, SyncCounter.value).where(SyncCounter.id == 1)
    ).one()

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
        dataset_id=dataset_id,
        next_since=upto,
        products=list(products),
        customers=list(customers),
        lots=list(lots),
        stock=list(stock),
    )
