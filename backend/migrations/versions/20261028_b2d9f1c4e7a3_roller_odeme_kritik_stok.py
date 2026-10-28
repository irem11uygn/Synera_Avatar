"""roller odeme kritik stok

Revision ID: b2d9f1c4e7a3
Revises: a7c41e2d9b10
Create Date: 2026-10-28 00:30:00.000000

Gerçek kullanım için:
- Yeni roller: DEPO, URETIM, KALITE, MAGAZA (her çalışan yalnız kendi ekranları).
- Yönetici şifre sıfırlayınca ilk girişte değiştirme zorunluluğu (users.must_change_password).
- Ürünlerde kritik stok seviyesi (products.min_stock).
- Satışlarda ödeme türü (sales.payment_method) — gün sonu kasa özeti için.
- Uyarı türü SKT_IHLALI: son kullanma tarihi geçmiş parti çevrimdışı satıldı.
- Depo/araç sayımı (stock_counts, stock_count_lines): eksik fire olarak düşülür.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "b2d9f1c4e7a3"
down_revision: str | None = "a7c41e2d9b10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_ROLES = ("YONETICI", "SATIS")
NEW_ROLES = ("YONETICI", "DEPO", "URETIM", "KALITE", "MAGAZA", "SATIS")
OLD_ALERTS = ("GERI_CAGIRMA_IHLALI",)
NEW_ALERTS = ("GERI_CAGIRMA_IHLALI", "SKT_IHLALI")
PAYMENTS = ("NAKIT", "KART", "HAVALE", "VERESIYE")


def upgrade() -> None:
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum(*OLD_ROLES, name="userrole"),
        type_=sa.Enum(*NEW_ROLES, name="userrole"),
        existing_nullable=False,
    )
    op.add_column(
        "users", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("products", sa.Column("min_stock", sa.Numeric(12, 3), nullable=True))
    op.add_column(
        "sales", sa.Column("payment_method", sa.Enum(*PAYMENTS, name="paymentmethod"), nullable=True)
    )
    op.alter_column(
        "alerts",
        "kind",
        existing_type=sa.Enum(*OLD_ALERTS, name="alertkind"),
        type_=sa.Enum(*NEW_ALERTS, name="alertkind"),
        existing_nullable=False,
    )
    op.create_table(
        "stock_counts",
        sa.Column("count_no", sa.String(length=30), nullable=False),
        sa.Column("warehouse_id", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_stock_counts_created_by_users")),
        sa.ForeignKeyConstraint(
            ["warehouse_id"], ["warehouses.id"], name=op.f("fk_stock_counts_warehouse_id_warehouses")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_counts")),
        sa.UniqueConstraint("count_no", name=op.f("uq_stock_counts_count_no")),
    )
    op.create_table(
        "stock_count_lines",
        sa.Column("count_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_id", sa.BigInteger(), nullable=False),
        sa.Column("system_qty", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("counted_qty", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("adjustment_id", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.CheckConstraint("counted_qty >= 0", name=op.f("ck_stock_count_lines_counted_qty_nonnegative")),
        sa.ForeignKeyConstraint(
            ["adjustment_id"], ["adjustments.id"], name=op.f("fk_stock_count_lines_adjustment_id_adjustments")
        ),
        sa.ForeignKeyConstraint(
            ["count_id"], ["stock_counts.id"], name=op.f("fk_stock_count_lines_count_id_stock_counts")
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], name=op.f("fk_stock_count_lines_lot_id_lots")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_count_lines")),
        sa.UniqueConstraint("adjustment_id", name=op.f("uq_stock_count_lines_adjustment_id")),
    )


def downgrade() -> None:
    op.drop_table("stock_count_lines")
    op.drop_table("stock_counts")
    op.execute("DELETE FROM alerts WHERE kind = 'SKT_IHLALI'")
    op.alter_column(
        "alerts",
        "kind",
        existing_type=sa.Enum(*NEW_ALERTS, name="alertkind"),
        type_=sa.Enum(*OLD_ALERTS, name="alertkind"),
        existing_nullable=False,
    )
    op.drop_column("sales", "payment_method")
    op.drop_column("products", "min_stock")
    op.drop_column("users", "must_change_password")
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum(*NEW_ROLES, name="userrole"),
        type_=sa.Enum(*OLD_ROLES, name="userrole"),
        existing_nullable=False,
    )
