"""iletisim kaydi kalite blokesi

Revision ID: e8a4c2f6b1d3
Revises: d7f3b9a2c4e1
Create Date: 2026-10-31 18:00:00.000000

- Geri çağırmada müşteriyle iletişim kaydı (recall_contacts): müşteri, sonuç (ulaşıldı / ulaşılamadı /
  ürün kalmamış), not, kim, ne zaman. Yalnız eklenir; müşterinin durumu son kaydıdır.
- Kalite blokesi (quality_holds): geri çağırmadan bağımsız karantina. Açıkken lot BLOKE'dur; kaldırılınca
  kayıt kalır. Var olan tablolara dokunulmaz, veri taşınmaz.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "e8a4c2f6b1d3"
down_revision: str | None = "d7f3b9a2c4e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")


def upgrade() -> None:
    op.create_table(
        "recall_contacts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("recall_id", sa.BigInteger(), nullable=False),
        sa.Column("partner_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "outcome",
            sa.Enum("ULASILDI", "ULASILAMADI", "URUN_KALMADI", name="contactoutcome"),
            nullable=False,
        ),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", TIMESTAMP, nullable=False),
        sa.ForeignKeyConstraint(
            ["recall_id"], ["recalls.id"], name=op.f("fk_recall_contacts_recall_id_recalls")
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"], ["partners.id"], name=op.f("fk_recall_contacts_partner_id_partners")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_recall_contacts_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recall_contacts")),
    )
    op.create_table(
        "quality_holds",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("lot_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("placed_by", sa.BigInteger(), nullable=True),
        sa.Column("placed_at", TIMESTAMP, nullable=False),
        sa.Column("released_by", sa.BigInteger(), nullable=True),
        sa.Column("released_at", TIMESTAMP, nullable=True),
        sa.Column("release_note", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], name=op.f("fk_quality_holds_lot_id_lots")),
        sa.ForeignKeyConstraint(["placed_by"], ["users.id"], name=op.f("fk_quality_holds_placed_by_users")),
        sa.ForeignKeyConstraint(
            ["released_by"], ["users.id"], name=op.f("fk_quality_holds_released_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quality_holds")),
    )


def downgrade() -> None:
    # Açık kalite blokesindeki lotlar geri çağırmada değilse yeniden satışa açılır; aksi hâlde eski
    # sürümde nedeni bilinmeyen bir BLOKE lot kalırdı.
    op.execute(
        "UPDATE lots SET status = 'AKTIF' WHERE id IN "
        "(SELECT lot_id FROM quality_holds WHERE released_at IS NULL) AND id NOT IN "
        "(SELECT rl.lot_id FROM recall_lots rl JOIN recalls r ON r.id = rl.recall_id WHERE r.status = 'ACIK')"
    )
    op.drop_table("quality_holds")
    op.drop_table("recall_contacts")
