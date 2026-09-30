"""Persist run decisions and replayable resume requests."""

import sqlalchemy as sa
from alembic import op

revision = "e14a217d0910"
down_revision = "d83ba105fc29"
branch_labels = None
depends_on = None


def common():
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade():
    op.create_table(
        "run_questions",
        *common(),
        sa.Column("pipeline_run_id", sa.Uuid(), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("execution_attempt_id", sa.Uuid(), sa.ForeignKey("execution_attempts.id", ondelete="SET NULL")),
        sa.Column("head_sha", sa.String(64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("resolution", sa.Text()),
    )
    op.create_index("ix_run_questions_pipeline_run_id", "run_questions", ["pipeline_run_id"])
    op.create_table(
        "run_answers",
        *common(),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("run_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("applied_attempt_id", sa.Uuid(), sa.ForeignKey("execution_attempts.id", ondelete="SET NULL")),
    )
    op.create_index("ix_run_answers_question_id", "run_answers", ["question_id"])
    op.create_table(
        "run_resume_receipts",
        *common(),
        sa.Column("pipeline_run_id", sa.Uuid(), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("execution_attempt_id", sa.Uuid(), sa.ForeignKey("execution_attempts.id", ondelete="SET NULL")),
    )
    op.create_index("ix_run_resume_receipts_pipeline_run_id", "run_resume_receipts", ["pipeline_run_id"])


def downgrade():
    op.drop_table("run_resume_receipts")
    op.drop_table("run_answers")
    op.drop_table("run_questions")
