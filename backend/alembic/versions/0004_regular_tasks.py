"""regular tasks: addressed offers, auto-check and rubric review

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-08 14:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("short_tasks") as batch:
        batch.add_column(sa.Column("mode", sa.String(length=16), nullable=False, server_default="approach"))
        # tasks published before this revision were open to the whole specialization
        batch.add_column(sa.Column("audience", sa.String(length=16), nullable=False, server_default="category"))
        batch.add_column(sa.Column("grade_id", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("job_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("competency_id", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("answer_spec", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("key_points", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("time_limit_days", sa.Integer(), nullable=False, server_default="7"))
        batch.add_column(sa.Column("max_offers", sa.Integer(), nullable=False, server_default="20"))
        batch.create_foreign_key("fk_short_tasks_grade_id_grades", "grades", ["grade_id"], ["id"])
        batch.create_foreign_key("fk_short_tasks_job_id_jobs", "jobs", ["job_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "task_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("short_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("offered_at", sa.DateTime(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("task_id", "candidate_id", name="uq_task_assignment"),
    )
    op.create_index("ix_task_assignments_task_id", "task_assignments", ["task_id"])
    op.create_index("ix_task_assignments_candidate_id", "task_assignments", ["candidate_id"])
    op.create_index("ix_task_assignments_status", "task_assignments", ["status"])

    with op.batch_alter_table("task_submissions") as batch:
        batch.add_column(sa.Column("assignment_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("status", sa.String(length=16), nullable=False, server_default="pending_review"))
        batch.add_column(sa.Column("auto_score", sa.Float(), nullable=True))
        batch.add_column(sa.Column("auto_detail", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("rubric", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("score", sa.Float(), nullable=True))
        batch.create_foreign_key("fk_task_submissions_assignment_id", "task_assignments", ["assignment_id"], ["id"],
                                 ondelete="SET NULL")
    # a former 1..5 rating becomes the final score
    op.execute("UPDATE task_submissions SET status = 'reviewed', score = (rating - 1) / 4.0 WHERE rating IS NOT NULL")


def downgrade() -> None:
    with op.batch_alter_table("task_submissions") as batch:
        batch.drop_constraint("fk_task_submissions_assignment_id", type_="foreignkey")
        for col in ("score", "rubric", "auto_detail", "auto_score", "status", "assignment_id"):
            batch.drop_column(col)
    op.drop_index("ix_task_assignments_status", table_name="task_assignments")
    op.drop_index("ix_task_assignments_candidate_id", table_name="task_assignments")
    op.drop_index("ix_task_assignments_task_id", table_name="task_assignments")
    op.drop_table("task_assignments")
    with op.batch_alter_table("short_tasks") as batch:
        batch.drop_constraint("fk_short_tasks_job_id_jobs", type_="foreignkey")
        batch.drop_constraint("fk_short_tasks_grade_id_grades", type_="foreignkey")
        for col in ("max_offers", "time_limit_days", "key_points", "answer_spec", "competency_id", "job_id",
                    "grade_id", "audience", "mode"):
            batch.drop_column(col)
