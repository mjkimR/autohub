"""Allow work plans to wait until a specified start time."""

import sqlalchemy as sa
from alembic import op

revision = "a36c439f2132"
down_revision = "f25b328e1021"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("work_plans", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("work_plans", "scheduled_at")
