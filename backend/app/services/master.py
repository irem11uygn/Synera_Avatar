"""Ana veri kartları: ürün ve cari (FR-101, FR-301)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInput
from app.models import Partner, Product, Warehouse
from app.models.enums import BaseUnit, WarehouseKind


def save_product(session: Session, product: Product | None, fields: dict[str, Any]) -> Product:
    """Yeni ürün açar (product=None) ya da var olanı günceller."""
    _check_unique_code(session, Product, fields["code"], product.id if product else None, "Ürün")
    if fields["base_unit"] == BaseUnit.ADET and not fields.get("unit_weight_kg"):
        raise InvalidInput("Adet ile izlenen üründe 1 adedin ağırlığı (kg) girilmeli.")
    return _save(session, product or Product(), fields)


def save_partner(session: Session, partner: Partner | None, fields: dict[str, Any]) -> Partner:
    _check_unique_code(session, Partner, fields["code"], partner.id if partner else None, "Cari")
    parent_id = fields.get("parent_id")
    if parent_id is not None and (partner is not None and parent_id == partner.id):
        raise InvalidInput("Bir cari kendisinin şubesi olamaz.")
    if parent_id is not None and session.get(Partner, parent_id) is None:
        raise InvalidInput("Ana firma bulunamadı.", parent_id=parent_id)
    saved = _save(session, partner or Partner(), fields)
    if saved.is_subcontractor:
        _ensure_subcontractor_warehouse(session, saved)
    return saved


def _ensure_subcontractor_warehouse(session: Session, partner: Partner) -> None:
    """Dış üreticiye sevk edilen hammadde onun deposunda izlenir (FR-106); deposu yoksa açılır."""
    exists = session.scalar(
        select(Warehouse.id).where(
            Warehouse.partner_id == partner.id, Warehouse.kind == WarehouseKind.DIS_URETICI
        )
    )
    if exists is not None:
        return
    code = f"DIS-{partner.code}"
    if len(code) > 30 or session.scalar(select(Warehouse.id).where(Warehouse.code == code)) is not None:
        code = f"DIS-C{partner.id}"
    session.add(
        Warehouse(
            code=code,
            name=f"{partner.name} deposu"[:100],
            kind=WarehouseKind.DIS_URETICI,
            partner_id=partner.id,
        )
    )
    session.flush()


def _save[T](session: Session, entity: T, fields: dict[str, Any]) -> T:
    for name, value in fields.items():
        setattr(entity, name, value)
    session.add(entity)
    session.flush()
    return entity


def _check_unique_code(session: Session, model: type, code: str, own_id: int | None, label: str) -> None:
    existing = session.scalar(select(model.id).where(model.code == code))  # type: ignore[attr-defined]
    if existing is not None and existing != own_id:
        raise InvalidInput(f"{label} kodu '{code}' zaten kullanılıyor.", code=code)
