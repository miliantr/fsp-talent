"""localization: user language, translations of items

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05 18:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("locale", sa.String(length=8), nullable=False, server_default="ru"))
    op.add_column("questions", sa.Column("i18n", sa.JSON(), nullable=True))
    op.add_column("test_items", sa.Column("i18n", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("test_items") as batch:
        batch.drop_column("i18n")
    with op.batch_alter_table("questions") as batch:
        batch.drop_column("i18n")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("locale")
