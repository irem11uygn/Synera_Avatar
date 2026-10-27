"""iade ve duzeltme hareket bagi

Revision ID: a7c41e2d9b10
Revises: e93069315efb
Create Date: 2026-10-27 12:00:00.000000

İade ve fire/imha kaydının stok hareketi, kaydın kendi kimliğini belge kimliği olarak taşır; bu yüzden
kayıt önce eklenir, hareket yazılır, hareket kimliği aynı işlemde kayda yazılır. Sütun bu sırayı
mümkün kılmak için boş geçilebilir oldu; işlem sonunda her kaydın hareketi vardır (servis bunu sağlar).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c41e2d9b10"
down_revision: str | None = "e93069315efb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("customer_returns", "adjustments")


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(table, "stock_movement_id", existing_type=sa.BigInteger(), nullable=True)


def downgrade() -> None:
    for table in TABLES:
        op.alter_column(table, "stock_movement_id", existing_type=sa.BigInteger(), nullable=False)
