"""Pin native specrig contracts and evidence on the shared PR run."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a92c095f8798"
down_revision = "f81b984e7687"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("specrig_snapshot", "specrig_progress"):
        op.add_column("pipeline_runs", sa.Column(name, sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True))

    op.add_column("run_resume_receipts", sa.Column("decision_evidence", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True))

def downgrade():
    op.drop_column("run_resume_receipts", "decision_evidence")
    op.drop_column("pipeline_runs", "specrig_progress")
    op.drop_column("pipeline_runs", "specrig_snapshot")
