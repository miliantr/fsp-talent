"""behavioural integrity of a test attempt: client events, time per item, pasted answers

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-08 16:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("test_attempts", sa.Column("client_events", sa.JSON(), nullable=True))
    op.add_column("test_attempts", sa.Column("integrity", sa.JSON(), nullable=True))
    op.add_column("test_answers", sa.Column("time_ms", sa.Integer(), nullable=True))
    op.add_column("test_answers", sa.Column("pasted", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("test_answers") as batch:
        batch.drop_column("pasted")
        batch.drop_column("time_ms")
    with op.batch_alter_table("test_attempts") as batch:
        batch.drop_column("integrity")
        batch.drop_column("client_events")
