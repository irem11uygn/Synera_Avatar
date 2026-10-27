"""Demo profili: şartnamenin zorunlu senaryosu kurulumdan hemen sonra hazır gelir (FR-309, CR-009).

'base' kayıtlarının üzerine, uygulamanın kendi servisleriyle (defter kuralları, maliyet, lot bağları
aynen geçerli) şunlar yazılır:

1. URT-2026-045: ET-2026-001 (100 kg) + BAH-2026-014 (2 kg) + BAG-2026-007 (5 kg) dış üreticiye
   sevk, 85 paket kabul, hizmet 85 × 5,50 € → SUC-2026-045, EKP 18,16 €.
2. SUC-2026-045'in 85 paketi satış aracına yüklenir; Android kanalından (satis1) Market A 30,
   Market B 25, Market C 30 paket satılır (SAT-2026-0101…0103). Araçta stok kalmaz.
3. Market B ikinci kademe dağıtımını bildirmiştir: Şube 1'e 15, Şube 2'ye 10 paket (kesin).
   Market A ve C bildirmemiştir: "bilinen son alıcı, sonrası bilinmiyor".
4. Görev 2: KUZU-2026-012'den 25 kg standart parçalama (değere göre dağıtım), but ve sırt
   araca yüklenir (Android'den satılabilir).

Geri çağırma başlatılmaz: demoda ET-2026-001 için canlı başlatılır.
"""

import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CuttingOutput, CuttingRecipe, Lot, Partner, Product, Sale, SaleLine, User, Warehouse
from app.models.enums import RecipeLineType, TransferReason
from app.models.types import utcnow
from app.services.cutting import approve_cutting, create_cutting, recipe_lines, record_actuals
from app.services.production import InputResult, PlannedInput, complete_order, create_order, ship_order
from app.services.returns import add_onward_delivery
from app.services.sales import SaleInput, SaleLineInput, push_sales
from app.services.transfers import TransferLineInput, create_transfer

logger = logging.getLogger(__name__)

# Sabit ad alanı: aynı demo her kurulumda aynı satış kimliklerini üretir (tekrar güvenliği bozulmaz).
_UUID_NS = uuid.UUID("6f1c2a52-6e3b-4c55-9a43-5b0f0f2d4a17")
SCENARIO_INPUTS = {"ET-2026-001": "100", "BAH-2026-014": "2", "BAG-2026-007": "5"}
MARKET_SALES = {"M-A": "30", "M-B": "25", "M-C": "30"}
ONWARD_B = {"M-B-S1": "15", "M-B-S2": "10"}
CUTTING_KG = {"KUZU-BUT": "7", "KUZU-SIRT": "4", "KUZU-OMUZ": "5", "KUZU-KABURGA": "3", "KUZU-KIYMA": "3"}
CUTTING_FIRE_KG = "3"
VAN_PARTS = ("KUZU-BUT", "KUZU-SIRT")


def build_demo_scenario(session: Session) -> None:
    admin = _by(session, User, username="yonetici")
    seller = _by(session, User, username="satis1")
    main = _by(session, Warehouse, code="ANA")
    van = _by(session, Warehouse, code="ARAC-01")
    lots = {lot.lot_no: lot for lot in session.scalars(select(Lot))}

    # 1. Dış üretim (Görev 1)
    order = create_order(
        session,
        subcontractor_id=_by(session, Partner, code="FSN-01").id,
        output_product_id=_by(session, Product, code="NARIN-SUCUK").id,
        planned_qty=Decimal(85),
        inputs=[PlannedInput(lots[no].id, Decimal(qty)) for no, qty in SCENARIO_INPUTS.items()],
        service_unit_price=Decimal("5.50"),
        user_id=admin.id,
    )
    ship_order(session, order.id, user_id=admin.id)
    complete_order(
        session,
        order.id,
        received_qty=Decimal(85),
        inputs=[InputResult(lots[no].id, Decimal(qty), Decimal(0)) for no, qty in SCENARIO_INPUTS.items()],
        service_invoice_no="FSN-2026-0311",
        user_id=admin.id,
    )
    sucuk = session.get(Lot, order.output_lot_id)
    assert sucuk is not None

    # 2. Araca yükleme ve Android kanalından satış
    create_transfer(
        session,
        from_warehouse_id=main.id,
        to_warehouse_id=van.id,
        lines=[TransferLineInput(sucuk.id, Decimal(85))],
        reason=TransferReason.ARAC_YUKLEME,
        user_id=admin.id,
    )
    product = session.get(Product, sucuk.product_id)
    assert product is not None and product.sale_price is not None
    sold_at = utcnow() - timedelta(hours=2)
    sales = [
        SaleInput(
            client_uuid=str(uuid.uuid5(_UUID_NS, f"demo-{code}")),
            customer_id=_by(session, Partner, code=code).id,
            warehouse_id=van.id,
            sold_at=sold_at + timedelta(minutes=20 * i),
            lines=[SaleLineInput(sucuk.lot_no, Decimal(qty), product.sale_price)],
        )
        for i, (code, qty) in enumerate(MARKET_SALES.items())
    ]
    results = push_sales(session, seller, "demo-emulator", sales)
    assert all(r.sale_no for r in results), results

    # 3. Market B'nin bildirdiği ikinci kademe dağıtım
    line_b = session.scalars(
        select(SaleLine)
        .join(Sale, Sale.id == SaleLine.sale_id)
        .where(Sale.customer_id == _by(session, Partner, code="M-B").id, SaleLine.lot_id == sucuk.id)
    ).one()
    for code, qty in ONWARD_B.items():
        add_onward_delivery(
            session,
            sale_line_id=line_b.id,
            recipient_partner_id=_by(session, Partner, code=code).id,
            qty=Decimal(qty),
            delivered_at=utcnow().date(),
            source_note="Market B'nin e-postayla bildirdiği şube dağıtımı",
            user_id=admin.id,
        )

    # 4. Parçalama (Görev 2) ve parçaların araca yüklenmesi
    recipe = _by(session, CuttingRecipe, code="KUZU-STD")
    cutting = create_cutting(
        session,
        recipe_id=recipe.id,
        input_lot_id=lots["KUZU-2026-012"].id,
        input_qty=Decimal(25),
        user_id=admin.id,
    )
    products = {p.id: p.code for p in session.scalars(select(Product))}
    actuals = {
        line.id: Decimal(
            CUTTING_FIRE_KG
            if line.line_type == RecipeLineType.FIRE
            else CUTTING_KG[products[line.product_id]]
        )
        for line in recipe_lines(session, recipe.id)
    }
    record_actuals(session, cutting.id, actuals=actuals)
    approve_cutting(session, cutting.id, user_id=admin.id)
    part_lots = session.execute(
        select(CuttingOutput.output_lot_id, CuttingOutput.actual_qty, CuttingOutput.product_id).where(
            CuttingOutput.cutting_id == cutting.id, CuttingOutput.output_lot_id.is_not(None)
        )
    ).all()
    create_transfer(
        session,
        from_warehouse_id=main.id,
        to_warehouse_id=van.id,
        lines=[
            TransferLineInput(lot_id, qty)
            for lot_id, qty, product_id in part_lots
            if products[product_id] in VAN_PARTS and lot_id is not None and qty is not None
        ],
        reason=TransferReason.ARAC_YUKLEME,
        user_id=admin.id,
    )
    session.flush()
    logger.info("Demo senaryosu yüklendi: %s → %s, %s.", order.order_no, sucuk.lot_no, cutting.cutting_no)


def _by[T](session: Session, model: type[T], **filters: str) -> T:
    query = select(model).filter_by(**filters)
    return session.scalars(query).one()
