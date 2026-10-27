"""'base' örnek kayıtları: şartname senaryosunun ana verileri."""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.config import get_settings
from app.models import (
    CuttingRecipe,
    CuttingRecipeLine,
    Lot,
    NumberSequence,
    Partner,
    Product,
    User,
    Warehouse,
)
from app.models.enums import BaseUnit, RecipeLineType, UserRole
from app.security import verify_password
from app.seed import load_profile
from tests.helpers import by_code, lot_by_no


def test_narin_sucuk_is_sold_in_1_kg_packages_at_vkp_24_90(session):
    sucuk = by_code(session, Product, "NARIN-SUCUK")
    assert (sucuk.base_unit, sucuk.unit_weight_kg, sucuk.sale_price, sucuk.lot_prefix) == (
        BaseUnit.ADET,
        Decimal("1.000"),
        Decimal("24.90"),
        "SUC",
    )


def test_raw_material_default_prices_match_specification(session):
    prices = {
        code: by_code(session, Product, code).default_purchase_price for code in ("ET", "BAHARAT", "BAGIRSAK")
    }
    assert prices == {"ET": Decimal("9.70"), "BAHARAT": Decimal("24.00"), "BAGIRSAK": Decimal("11.60")}


def test_markets_and_registered_second_tier_branches(session):
    customers = session.scalars(select(Partner.name).where(Partner.is_customer).order_by(Partner.name)).all()
    assert customers == ["Market A", "Market B", "Market C", "Perakende müşteri"]
    market_b = by_code(session, Partner, "M-B")
    branches = session.scalars(select(Partner.code).where(Partner.parent_id == market_b.id)).all()
    assert sorted(branches) == ["M-B-S1", "M-B-S2"]
    assert all(by_code(session, Partner, c).email for c in ("M-A", "M-B", "M-C"))  # geri çağırma iletişimi


def test_lamb_recipe_ratios_sum_to_one_and_fire_bears_no_cost(session):
    recipe = by_code(session, CuttingRecipe, "KUZU-STD")
    lines = session.scalars(
        select(CuttingRecipeLine)
        .where(CuttingRecipeLine.recipe_id == recipe.id)
        .order_by(CuttingRecipeLine.sort_order)
    ).all()
    assert sum(line.standard_ratio for line in lines) == Decimal("1.0000")
    fire = [line for line in lines if line.line_type == RecipeLineType.FIRE]
    assert len(fire) == 1 and fire[0].product_id is None and not fire[0].bears_cost
    assert recipe.tolerance_kg == Decimal("0.200")


def test_demo_users_and_sales_vehicle(session):
    satis = session.scalars(select(User).where(User.username == "satis1")).one()
    assert satis.role == UserRole.SATIS
    assert satis.warehouse_id == by_code(session, Warehouse, "ARAC-01").id
    yonetici = session.scalars(select(User).where(User.username == "yonetici")).one()
    assert verify_password("yonetici123", yonetici.password_hash)
    assert not verify_password("yanlis", yonetici.password_hash)


def test_first_production_order_number_will_be_045(session):
    """Şartname senaryosu: URT-2026-045."""
    sequence = session.scalars(
        select(NumberSequence).where(NumberSequence.prefix == "URT", NumberSequence.year == 2026)
    ).one()
    assert sequence.last_no + 1 == 45


def test_scenario_raw_material_lots_are_in_main_warehouse(session):
    """ET-2026-001 / 100 kg (şartname), baharat ve bağırsak lotları, kuzu lotu 351,00 €."""
    expected = {
        "ET-2026-001": (Decimal("100"), Decimal("970.00")),
        "BAH-2026-014": (Decimal("2"), Decimal("48.00")),
        "BAG-2026-007": (Decimal("5"), Decimal("58.00")),
        "KUZU-2026-012": (Decimal("25"), Decimal("351.00")),
    }
    lots = session.scalars(select(Lot).where(Lot.lot_no.in_(expected))).all()
    assert {lot.lot_no: (lot.remaining_qty, lot.remaining_value) for lot in lots} == expected
    assert lot_by_no(session, "ET-2026-001").supplier_id == by_code(session, Partner, "TED-ET").id


def test_synced_master_data_has_change_numbers(session):
    assert session.scalar(select(func.min(Product.change_seq))) > 0
    assert session.scalar(select(func.min(Partner.change_seq))) > 0


def test_seed_does_not_load_twice(session):
    before = session.scalar(select(func.count()).select_from(Product))
    assert load_profile(session, get_settings().seed_dir, "base") is False
    assert session.scalar(select(func.count()).select_from(Product)) == before


def test_unknown_profile_is_rejected(session):
    with pytest.raises(ValueError, match="Bilinmeyen SEED_PROFILE"):
        load_profile(session, get_settings().seed_dir, "yok")
