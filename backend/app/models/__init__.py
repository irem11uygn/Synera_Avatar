"""SQLAlchemy tabloları. Alembic'in görmesi için bütün model modülleri burada içe aktarılır."""

from app.db import Base
from app.models.ai import AiForecast
from app.models.cutting import Cutting, CuttingOutput, CuttingRecipe, CuttingRecipeLine
from app.models.inventory import Lot, LotLink, StockBalance, StockMovement
from app.models.master import AuthSession, NumberSequence, Partner, Product, User, Warehouse
from app.models.production import ProductionInput, ProductionOrder
from app.models.purchasing import Purchase, PurchaseCost, PurchaseLine
from app.models.recall import Alert, Recall, RecallLot
from app.models.sales import CustomerReturn, OnwardDelivery, Sale, SaleLine
from app.models.sync import SyncCounter
from app.models.transfers import Adjustment, StockCount, StockCountLine, Transfer, TransferLine

__all__ = [
    "Adjustment",
    "AiForecast",
    "Alert",
    "AuthSession",
    "Base",
    "CustomerReturn",
    "Cutting",
    "CuttingOutput",
    "CuttingRecipe",
    "CuttingRecipeLine",
    "Lot",
    "LotLink",
    "NumberSequence",
    "OnwardDelivery",
    "Partner",
    "Product",
    "ProductionInput",
    "ProductionOrder",
    "Purchase",
    "PurchaseCost",
    "PurchaseLine",
    "Recall",
    "RecallLot",
    "Sale",
    "SaleLine",
    "StockBalance",
    "StockCount",
    "StockCountLine",
    "StockMovement",
    "SyncCounter",
    "Transfer",
    "TransferLine",
    "User",
    "Warehouse",
]
