"""senkron veri kumesi kimligi

Revision ID: e93069315efb
Revises: df3690a4b5d8
Create Date: 2026-10-24 11:43:41.306159

Veritabanı her sıfırdan kurulduğunda yeni bir UUID alır. Android cihaz bu kimliği değişmiş görürse
yerel kopyasını silip baştan çeker (sıfırdan kurulan sunucuda artımlı çekme eski kayıtları bırakırdı).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e93069315efb"
down_revision: str | None = "df3690a4b5d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sync_counter", sa.Column("dataset_id", sa.String(length=36), nullable=True))
    op.execute("UPDATE sync_counter SET dataset_id = UUID() WHERE id = 1")
    op.alter_column("sync_counter", "dataset_id", existing_type=sa.String(length=36), nullable=False)


def downgrade() -> None:
    op.drop_column("sync_counter", "dataset_id")
