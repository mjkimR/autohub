"""Retain opt-in decision subscriptions and uncertain delivery evidence."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a471ce28d100"
down_revision = "f36a539dc10e"
branch_labels = None
depends_on = None


def identity():
    return [sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now())]


def channel():
    return sa.Column("channel_id",sa.Uuid(),sa.ForeignKey("notification_channels.id",ondelete="CASCADE"),nullable=False)


def upgrade():
    j = sa.JSON().with_variant(postgresql.JSONB(),"postgresql")
    op.add_column("notification_channels",sa.Column("destination_generation",sa.Integer(),nullable=False,server_default="0"))
    op.create_table("decision_subscriptions",sa.Column("channel_id",sa.Uuid(),sa.ForeignKey("notification_channels.id",ondelete="CASCADE"),primary_key=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("revision",sa.Integer(),nullable=False),sa.Column("enabled",sa.Boolean(),nullable=False),sa.Column("settings",j,nullable=False),sa.Column("scan_time",sa.DateTime(timezone=True)),sa.Column("scan_key",sa.String(255)),sa.Column("digest_since",sa.DateTime(timezone=True)))
    op.create_table("decision_notices",*identity(),channel(),sa.Column("destination_generation",sa.Integer(),nullable=False),sa.Column("decision_key",sa.String(255),nullable=False),sa.Column("fingerprint",sa.String(64),nullable=False),sa.Column("state",sa.String(20),nullable=False),sa.Column("last_attempt_id",sa.Uuid()),sa.Column("observed",j,nullable=False),sa.UniqueConstraint("channel_id","destination_generation","decision_key","fingerprint",name="uq_decision_notice_generation"))
    op.create_index("ix_decision_notices_channel_id","decision_notices",["channel_id"])
    op.create_table("decision_notice_attempts",*identity(),channel(),sa.Column("destination_generation",sa.Integer(),nullable=False),sa.Column("notice_ids",j,nullable=False),sa.Column("message",sa.Text(),nullable=False),sa.Column("state",sa.String(20),nullable=False),sa.Column("token",sa.Uuid(),nullable=False),sa.Column("lease_expires_at",sa.DateTime(timezone=True),nullable=False),sa.Column("outcome_at",sa.DateTime(timezone=True)),sa.Column("detail",sa.String(100)))
    op.create_index("ix_decision_notice_attempts_channel_id","decision_notice_attempts",["channel_id"])
    op.create_table("decision_notice_requests",*identity(),channel(),sa.Column("operation",sa.String(20),nullable=False),sa.Column("request_id",sa.Uuid(),nullable=False),sa.Column("actor",sa.String(255),nullable=False),sa.Column("digest",sa.String(64),nullable=False),sa.Column("result",j,nullable=False),sa.UniqueConstraint("channel_id","operation","request_id",name="uq_decision_notice_request"))
    op.create_table("decision_notice_queue",sa.Column("name",sa.String(50),primary_key=True),sa.Column("cursor",sa.String(36),nullable=False))


def downgrade():
    for table in ["decision_notice_queue","decision_notice_requests","decision_notice_attempts","decision_notices","decision_subscriptions"]:
        op.drop_table(table)
    op.drop_column("notification_channels","destination_generation")
