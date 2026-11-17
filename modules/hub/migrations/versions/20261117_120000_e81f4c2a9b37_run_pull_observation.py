"""Retain the last observed PR Draft status and CI verification on each run."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e81f4c2a9b37"
down_revision = "d704fb51a433"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable without a default: existing runs read as "not yet observed" until their next CI observation.
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.add_column(sa.Column("pull_observation", json_type, nullable=True))


def downgrade():
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.drop_column("pull_observation")
