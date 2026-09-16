"""Remember the AI catalog a pull request run was enrolled with by name.

``pipeline_runs.requested_catalog_id`` holds a catalog designated at enrollment (``@auto-run:<key or kind>``
or the enroll request). Such a run keeps that catalog across project changes and resumes; without one, a run
follows the project's catalog selection as before.

Revision ID: c5d6e7f8a9b0
Revises: e0f1a2b3c4d5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d6e7f8a9b0"
down_revision: str | None = "e0f1a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.add_column(sa.Column("requested_catalog_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_pipeline_runs_requested_catalog_id", "ai_catalogs", ["requested_catalog_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.drop_constraint("fk_pipeline_runs_requested_catalog_id", type_="foreignkey")
        batch.drop_column("requested_catalog_id")
