"""several verified categories per candidate (one per specialization)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-08 12:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidate_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("specialization_id", sa.String(length=32), sa.ForeignKey("specializations.id"), nullable=False),
        sa.Column("grade_id", sa.String(length=16), sa.ForeignKey("grades.id"), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("theta", sa.Float(), nullable=False),
        sa.Column("scaled_score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("competency_scores", sa.JSON(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=False),
        sa.Column("grade_locked_until", sa.DateTime(), nullable=True),
        sa.Column("upgrade_eligible", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("candidate_id", "specialization_id", name="uq_candidate_category"),
    )
    op.create_index("ix_candidate_categories_candidate_id", "candidate_categories", ["candidate_id"])
    op.create_index("ix_candidate_categories_specialization_id", "candidate_categories", ["specialization_id"])
    op.create_index("ix_candidate_categories_grade_id", "candidate_categories", ["grade_id"])
    # the single category of existing profiles becomes their primary category
    op.execute("""
        INSERT INTO candidate_categories (candidate_id, specialization_id, grade_id, is_primary, theta,
            scaled_score, confidence, competency_scores, verified_at, grade_locked_until, upgrade_eligible,
            created_at)
        SELECT id, verified_specialization_id, verified_grade_id, TRUE, COALESCE(ability_theta, 0),
            COALESCE(scaled_score, 0), COALESCE(category_confidence, 0.5), competency_scores,
            COALESCE(verified_at, created_at), grade_locked_until, upgrade_eligible, COALESCE(verified_at, created_at)
        FROM candidate_profiles
        WHERE verified_grade_id IS NOT NULL AND verified_specialization_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_candidate_categories_grade_id", table_name="candidate_categories")
    op.drop_index("ix_candidate_categories_specialization_id", table_name="candidate_categories")
    op.drop_index("ix_candidate_categories_candidate_id", table_name="candidate_categories")
    op.drop_table("candidate_categories")
