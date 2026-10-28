"""alarm denetim eposta

Revision ID: c5e8a1f0d2b6
Revises: b2d9f1c4e7a3
Create Date: 2026-10-28 18:00:00.000000

Alarm merkezi, denetim günlüğü ve e-posta:
- Uyarılara önem (severity), kimin okundu işaretlediği ve kural anahtarı (aynı durum için tek alarm).
- Yeni uyarı türleri: geri çağırma başlatıldı, bloke lot satış denemesi, bloke lotta stok,
  verim sapması, alış fiyatı artışı, art arda hatalı giriş.
- Denetim günlüğü (audit_events), alarm eşikleri (app_settings), e-posta giden kutusu (mail_outbox).
- Kullanıcılarda e-posta adresi.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "c5e8a1f0d2b6"
down_revision: str | None = "b2d9f1c4e7a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_ALERTS = ("GERI_CAGIRMA_IHLALI", "SKT_IHLALI")
NEW_ALERTS = (
    *OLD_ALERTS,
    "GERI_CAGIRMA",
    "BLOKE_SATIS_DENEMESI",
    "BLOKE_STOK",
    "VERIM_SAPMASI",
    "FIYAT_ARTISI",
    "HATALI_GIRIS",
)
SEVERITY = sa.Enum("BILGI", "UYARI", "KRITIK", name="severity")
TIMESTAMP = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")


def upgrade() -> None:
    op.alter_column(
        "alerts",
        "kind",
        existing_type=sa.Enum(*OLD_ALERTS, name="alertkind"),
        type_=sa.Enum(*NEW_ALERTS, name="alertkind"),
        existing_nullable=False,
    )
    op.add_column("alerts", sa.Column("severity", SEVERITY, nullable=False, server_default="UYARI"))
    # Var olan geri çağırma ihlalleri kritik: geri çağrılmış ürün müşteriye gitmiş.
    op.execute("UPDATE alerts SET severity = 'KRITIK' WHERE kind = 'GERI_CAGIRMA_IHLALI'")
    op.add_column("alerts", sa.Column("acknowledged_by", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_alerts_acknowledged_by_users"), "alerts", "users", ["acknowledged_by"], ["id"]
    )
    op.add_column("alerts", sa.Column("rule_key", sa.String(length=120), nullable=True))
    op.create_unique_constraint(op.f("uq_alerts_rule_key"), "alerts", ["rule_key"])
    op.add_column("users", sa.Column("email", sa.String(length=120), nullable=True))

    op.create_table(
        "audit_events",
        sa.Column("created_at", TIMESTAMP, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=50), nullable=True),
        sa.Column("severity", SEVERITY, nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("ref_type", sa.String(length=30), nullable=True),
        sa.Column("ref_id", sa.BigInteger(), nullable=True),
        sa.Column("client", sa.String(length=64), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_audit_events_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(op.f("ix_audit_events_created_at"), "audit_events", ["created_at"])
    op.create_index(op.f("ix_audit_events_username"), "audit_events", ["username"])
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.String(length=200), nullable=False),
        sa.Column("updated_at", TIMESTAMP, nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name=op.f("fk_app_settings_updated_by_users")),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_app_settings")),
    )
    op.create_table(
        "mail_outbox",
        sa.Column("created_at", TIMESTAMP, nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("recipients", sa.String(length=1000), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("KUYRUKTA", "GONDERILDI", "HATA", name="mailstatus"), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("sent_at", TIMESTAMP, nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("alert_id", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], name=op.f("fk_mail_outbox_alert_id_alerts")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_mail_outbox_created_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mail_outbox")),
    )


def downgrade() -> None:
    op.drop_table("mail_outbox")
    op.drop_table("app_settings")
    op.drop_index(op.f("ix_audit_events_username"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_created_at"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_column("users", "email")
    op.drop_constraint(op.f("uq_alerts_rule_key"), "alerts", type_="unique")
    op.drop_column("alerts", "rule_key")
    op.drop_constraint(op.f("fk_alerts_acknowledged_by_users"), "alerts", type_="foreignkey")
    op.drop_column("alerts", "acknowledged_by")
    op.drop_column("alerts", "severity")
    op.execute(f"DELETE FROM alerts WHERE kind NOT IN {OLD_ALERTS}")
    op.alter_column(
        "alerts",
        "kind",
        existing_type=sa.Enum(*NEW_ALERTS, name="alertkind"),
        type_=sa.Enum(*OLD_ALERTS, name="alertkind"),
        existing_nullable=False,
    )
