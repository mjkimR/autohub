"""Retain selected native SDD batches and exact admission checkpoints."""
from typing import cast

import sqlalchemy as sa
from alembic import op

revision = "e25f428cba0f"
down_revision = "d14e317ba9be"
branch_labels = None
depends_on = None


def upgrade():
    # The new tables have no legacy rows to backfill. Use the exact model schema for dialect parity.
    from app.features.project_management.sdd.batch_models import (
        SddActivityClaim, SddBatch, SddBatchControl, SddBatchMember,
    )
    for model in (SddBatch, SddBatchMember, SddActivityClaim, SddBatchControl):
        cast(sa.Table, model.__table__).create(op.get_bind())


def downgrade():
    for name in ("sdd_batch_controls", "sdd_activity_claims", "sdd_batch_members", "sdd_batches"):
        op.drop_table(name)
