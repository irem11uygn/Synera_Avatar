"""eposta bildirim abonelik

Revision ID: d7f3b9a2c4e1
Revises: c5e8a1f0d2b6
Create Date: 2026-10-28 20:00:00.000000

E-posta bildirimleri:
- Alarm abonelikleri (alert_subscriptions): kullanıcı × alarm türü, açık/kapalı. Kayıt yoksa rolün
  varsayılanı geçerlidir; bu yüzden tablo boş başlar.
- Giden kutusunda HTML gövde, tek ek (ad, tür, içerik) ve tekilleştirme anahtarı (aynı alarm aynı
  alıcıya bir kez).
- Yeni uyarı türleri: SKT yaklaşan/geçen lot, sayım farkı.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "d7f3b9a2c4e1"
down_revision: str | None = "c5e8a1f0d2b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_ALERTS = (
    "GERI_CAGIRMA_IHLALI",
    "SKT_IHLALI",
    "GERI_CAGIRMA",
    "BLOKE_SATIS_DENEMESI",
    "BLOKE_STOK",
    "VERIM_SAPMASI",
    "FIYAT_ARTISI",
    "HATALI_GIRIS",
)
NEW_ALERTS = (*OLD_ALERTS, "SKT_YAKLASIYOR", "SAYIM_FARKI")
TIMESTAMP = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")


def upgrade() -> None:
    op.alter_column(
        "alerts",
        "kind",
        existing_type=sa.Enum(*OLD_ALERTS, name="alertkind"),
        type_=sa.Enum(*NEW_ALERTS, name="alertkind"),
        existing_nullable=False,
    )
    op.create_table(
        "alert_subscriptions",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("alert_type", sa.Enum(*NEW_ALERTS, name="alertkind"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_alert_subscriptions_user_id_users")),
        sa.PrimaryKeyConstraint("user_id", "alert_type", name=op.f("pk_alert_subscriptions")),
    )
    op.add_column("mail_outbox", sa.Column("html", sa.Text(), nullable=True))
    op.add_column("mail_outbox", sa.Column("attachment_name", sa.String(length=200), nullable=True))
    op.add_column("mail_outbox", sa.Column("attachment_mime", sa.String(length=100), nullable=True))
    op.add_column(
        "mail_outbox",
        sa.Column("attachment", sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql"), nullable=True),
    )
    op.add_column("mail_outbox", sa.Column("dedup_key", sa.String(length=150), nullable=True))
    op.create_unique_constraint(op.f("uq_mail_outbox_dedup_key"), "mail_outbox", ["dedup_key"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_mail_outbox_dedup_key"), "mail_outbox", type_="unique")
    for column in ("dedup_key", "attachment", "attachment_mime", "attachment_name", "html"):
        op.drop_column("mail_outbox", column)
    op.drop_table("alert_subscriptions")
    new_kinds = "('SKT_YAKLASIYOR', 'SAYIM_FARKI')"
    op.execute(
        "UPDATE mail_outbox SET alert_id = NULL "
        f"WHERE alert_id IN (SELECT id FROM alerts WHERE kind IN {new_kinds})"
    )
    op.execute(f"DELETE FROM alerts WHERE kind IN {new_kinds}")
    op.alter_column(
        "alerts",
        "kind",
        existing_type=sa.Enum(*NEW_ALERTS, name="alertkind"),
        type_=sa.Enum(*OLD_ALERTS, name="alertkind"),
        existing_nullable=False,
    )
