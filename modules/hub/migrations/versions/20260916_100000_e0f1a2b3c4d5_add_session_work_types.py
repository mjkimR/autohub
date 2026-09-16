"""Give catalog sessions a work type and a result.

- ``ai_catalog_sessions.work_type`` says what a session is for: ``task`` work converges on a pull request that
  the hub adopts into the matching project's pipeline run (``pipeline_run_id``); a ``report`` ends as the
  session's final message (``result_summary``).
- ``ai_catalog_sessions.repository`` records the GitHub repository the session worked in, so its pull request
  can be matched to a project.

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e0f1a2b3c4d5"
down_revision: str | None = "d9e0f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("ai_catalog_sessions") as batch:
        batch.add_column(sa.Column("work_type", sa.String(20), server_default="task", nullable=False))
        batch.add_column(sa.Column("repository", sa.String(255), nullable=True))
        batch.add_column(sa.Column("pipeline_run_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("result_summary", sa.Text(), nullable=True))
        batch.create_foreign_key(
            "fk_ai_catalog_sessions_pipeline_run_id", "pipeline_runs", ["pipeline_run_id"], ["id"], ondelete="SET NULL"
        )
    op.create_index(
        "ix_ai_catalog_sessions_pipeline_run_id", "ai_catalog_sessions", ["pipeline_run_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_ai_catalog_sessions_pipeline_run_id", table_name="ai_catalog_sessions")
    with op.batch_alter_table("ai_catalog_sessions") as batch:
        batch.drop_constraint("fk_ai_catalog_sessions_pipeline_run_id", type_="foreignkey")
        batch.drop_column("result_summary")
        batch.drop_column("pipeline_run_id")
        batch.drop_column("repository")
        batch.drop_column("work_type")
