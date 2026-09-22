"""Keep a Jules adoption verdict when pipeline run retention removes its history."""

import sqlalchemy as sa
from alembic import op

revision = "a5e6f7a8b9c0"
down_revision = "f4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_catalog_sessions", sa.Column("pipeline_run_retired_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    # Older code uses failure_detail as the persistent non-adoption verdict.
    op.execute("""
        UPDATE ai_catalog_sessions
        SET failure_detail = 'Pipeline run history expired; do not re-adopt this pull request'
        WHERE pipeline_run_retired_at IS NOT NULL AND pipeline_run_id IS NULL AND failure_detail IS NULL
    """)
    op.drop_column("ai_catalog_sessions", "pipeline_run_retired_at")
