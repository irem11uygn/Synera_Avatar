"""Boş veritabanına örnek kayıtları yükler (SEED_PROFILE: none | base | demo).

- base: ana veriler + hammadde alışları.
- demo (varsayılan): base + şartnamenin zorunlu senaryosu ve örnek parçalama (app/demo.py, FR-309).

Çalıştırma: python -m app.seed  (API konteyneri açılışta kendisi çalıştırır).
"""

import json
import logging
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_sessionmaker
from app.demo import build_demo_scenario
from app.domain.clock import business_today
from app.models import CuttingRecipe, CuttingRecipeLine, NumberSequence, Partner, Product, User, Warehouse
from app.models.enums import (
    AllocationMethod,
    BaseUnit,
    ProductKind,
    PurchaseCostKind,
    RecipeLineType,
    Species,
    UserRole,
    WarehouseKind,
)
from app.security import hash_password
from app.services.purchasing import ExtraCost, PurchaseLineInput, create_purchase

logger = logging.getLogger(__name__)

PROFILES = ("none", "base", "demo")


def load_profile(
    session: Session, seed_dir: Path, profile: str, *, temporary_passwords: bool = False
) -> bool:
    """Profili yükler ve True döner. Veritabanında ürün varsa hiçbir şey yapmaz (False).

    temporary_passwords: örnek kullanıcıların (README'de yazan) şifreleri geçici sayılır; ilk girişte
    değiştirilmeden hiçbir işlem yapılamaz. Demo dışındaki kurulumlarda açıktır (bkz. main).
    """
    if profile not in PROFILES:
        raise ValueError(f"Bilinmeyen SEED_PROFILE: {profile!r} (geçerli: {', '.join(PROFILES)})")
    if profile == "none":
        return False
    if session.scalar(select(func.count()).select_from(Product)):
        logger.info("Veritabanı boş değil; örnek kayıtlar yüklenmedi.")
        return False

    data = json.loads((seed_dir / "base.json").read_text(encoding="utf-8"))
    partners = _load_partners(session, data["partners"])
    warehouses = _load_warehouses(session, data["warehouses"], partners)
    products = _load_products(session, data["products"])
    _load_users(session, data["users"], warehouses, temporary_passwords)
    _load_recipes(session, data["cutting_recipes"], products)
    for row in data["number_sequences"]:
        session.add(NumberSequence(prefix=row["prefix"], year=row["year"], last_no=row["last_no"]))
    session.flush()
    _load_purchases(session, data["purchases"], partners, warehouses, products)
    if profile == "demo":
        build_demo_scenario(session)
    logger.info(
        "'%s' profili yüklendi: %d ürün, %d cari, %d alış.",
        profile,
        len(products),
        len(partners),
        len(data["purchases"]),
    )
    return True


def _dec(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def _load_partners(session: Session, rows: list[dict[str, Any]]) -> dict[str, Partner]:
    partners: dict[str, Partner] = {}
    for row in rows:  # ana firma, şubesinden önce gelir
        parent = partners[row["parent_code"]] if "parent_code" in row else None
        partner = Partner(
            code=row["code"],
            name=row["name"],
            is_supplier=row.get("is_supplier", False),
            is_customer=row.get("is_customer", False),
            is_subcontractor=row.get("is_subcontractor", False),
            parent_id=parent.id if parent else None,
            contact_person=row.get("contact_person"),
            phone=row.get("phone"),
            email=row.get("email"),
            address=row.get("address"),
        )
        session.add(partner)
        session.flush()
        partners[partner.code] = partner
    return partners


def _load_warehouses(
    session: Session, rows: list[dict[str, Any]], partners: dict[str, Partner]
) -> dict[str, Warehouse]:
    warehouses = {
        row["code"]: Warehouse(
            code=row["code"],
            name=row["name"],
            kind=WarehouseKind(row["kind"]),
            partner_id=partners[row["partner_code"]].id if "partner_code" in row else None,
        )
        for row in rows
    }
    session.add_all(warehouses.values())
    session.flush()
    return warehouses


def _load_products(session: Session, rows: list[dict[str, Any]]) -> dict[str, Product]:
    products = {
        row["code"]: Product(
            code=row["code"],
            name=row["name"],
            kind=ProductKind(row["kind"]),
            base_unit=BaseUnit(row["base_unit"]),
            unit_weight_kg=_dec(row.get("unit_weight_kg")),
            lot_prefix=row.get("lot_prefix"),
            default_purchase_price=_dec(row.get("default_purchase_price")),
            sale_price=_dec(row.get("sale_price")),
            shelf_life_days=row.get("shelf_life_days"),
            min_stock=_dec(row.get("min_stock")),
        )
        for row in rows
    }
    session.add_all(products.values())
    session.flush()
    return products


def _load_users(
    session: Session, rows: list[dict[str, Any]], warehouses: dict[str, Warehouse], temporary_passwords: bool
) -> None:
    for row in rows:
        warehouse = warehouses[row["warehouse_code"]] if "warehouse_code" in row else None
        session.add(
            User(
                username=row["username"],
                full_name=row["full_name"],
                role=UserRole(row["role"]),
                password_hash=hash_password(row["password"]),
                warehouse_id=warehouse.id if warehouse else None,
                email=row.get("email"),
                must_change_password=temporary_passwords,
            )
        )


def _load_recipes(session: Session, rows: list[dict[str, Any]], products: dict[str, Product]) -> None:
    for row in rows:
        recipe = CuttingRecipe(
            code=row["code"],
            name=row["name"],
            input_product_id=products[row["input_product_code"]].id,
            species=Species(row["species"]),
            default_method=AllocationMethod(row["default_method"]),
            tolerance_kg=Decimal(row["tolerance_kg"]),
        )
        session.add(recipe)
        session.flush()
        for sort_order, line in enumerate(row["lines"], start=1):
            session.add(
                CuttingRecipeLine(
                    recipe_id=recipe.id,
                    line_type=RecipeLineType(line["line_type"]),
                    product_id=products[line["product_code"]].id if "product_code" in line else None,
                    standard_ratio=Decimal(line["standard_ratio"]),
                    value_per_kg=_dec(line.get("value_per_kg")),
                    bears_cost=line.get("bears_cost", True),
                    sort_order=sort_order,
                )
            )


def _purchase_date(row: dict[str, Any]) -> date:
    """Örnek alış tarihi kurulum gününe göredir: demo hangi gün kurulursa kurulsun lotların son kullanma
    tarihi geçmemiş olur. Sabit tarih de verilebilir ("doc_date")."""
    if "doc_date" in row:
        return date.fromisoformat(row["doc_date"])
    return business_today() - timedelta(days=row.get("days_before_install", 1))


def _load_purchases(
    session: Session,
    rows: list[dict[str, Any]],
    partners: dict[str, Partner],
    warehouses: dict[str, Warehouse],
    products: dict[str, Product],
) -> None:
    """Alışlar doğrudan tabloya değil, alış servisi ve stok defteri üzerinden yazılır."""
    for row in rows:
        create_purchase(
            session,
            supplier_id=partners[row["supplier_code"]].id,
            doc_no=row["doc_no"],
            doc_date=_purchase_date(row),
            warehouse_id=warehouses[row["warehouse_code"]].id,
            lines=[
                PurchaseLineInput(
                    product_id=products[line["product_code"]].id,
                    lot_no=line["lot_no"],
                    qty=Decimal(line["qty"]),
                    unit_price=Decimal(line["unit_price"]),
                    extra_costs=[
                        ExtraCost(PurchaseCostKind(cost["kind"]), Decimal(cost["amount"]), cost.get("note"))
                        for cost in line.get("extra_costs", [])
                    ],
                )
                for line in row["lines"]
            ],
        )


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    demo = settings.seed_profile == "demo"
    with get_sessionmaker()() as session, session.begin():
        loaded = load_profile(session, settings.seed_dir, settings.seed_profile, temporary_passwords=not demo)
    if demo:
        # Yarışma demosu için bilinen şifreler kasıtlıdır; gerçek kurulumda bu profil kullanılmamalı.
        logger.warning(
            "SEED_PROFILE=demo: örnek kullanıcıların şifreleri README'de yazılı (yalnız yerel demo). "
            "Gerçek kullanımda SEED_PROFILE=base ya da none kullanın."
        )
    elif loaded:
        logger.warning("Örnek kullanıcıların şifreleri geçicidir: ilk girişte değiştirilmeleri zorunlu.")


if __name__ == "__main__":
    main()
