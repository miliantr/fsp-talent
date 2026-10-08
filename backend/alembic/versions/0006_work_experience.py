"""places of work in the candidate profile

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-08 18:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidate_experience",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("company", sa.String(length=128), nullable=False),
        sa.Column("position", sa.String(length=128), nullable=False),
        sa.Column("period_from", sa.String(length=7), nullable=False),
        sa.Column("period_to", sa.String(length=7), nullable=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_candidate_experience_candidate_id", "candidate_experience", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_candidate_experience_candidate_id", table_name="candidate_experience")
    op.drop_table("candidate_experience")
