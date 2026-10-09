"""Persist SDK catalogs, flow checkpoints, attempts and command receipts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "d69f762c5465"
down_revision = "c58e651b4354"
branch_labels = None
depends_on = None
JSON_TYPE = sa.JSON().with_variant(JSONB, "postgresql")


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def identifier():
    return sa.Column("id", sa.Uuid(), primary_key=True)


def upgrade():
    op.create_table(
        "sdk_flow_environments",
        sa.Column("provider", sa.String(64), primary_key=True),
        sa.Column("environment", sa.String(64), primary_key=True),
        sa.Column("owner_machine_id", sa.Uuid(), nullable=False),
        sa.Column("active_release_id", sa.String(128)),
        sa.Column("revision", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "sdk_flow_releases",
        identifier(),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("environment", sa.String(64), nullable=False),
        sa.Column("release_id", sa.String(128), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("definition", JSON_TYPE, nullable=False),
        sa.Column("bindings", JSON_TYPE, nullable=False),
        sa.ForeignKeyConstraint(
            ["provider", "environment"], ["sdk_flow_environments.provider", "sdk_flow_environments.environment"]
        ),
        sa.UniqueConstraint("provider", "environment", "release_id", name="uq_sdk_flow_release_identity"),
        *timestamps(),
    )
    op.create_table(
        "sdk_flow_runs",
        identifier(),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("environment", sa.String(64), nullable=False),
        sa.Column("release_pk", sa.Uuid(), sa.ForeignKey("sdk_flow_releases.id"), nullable=False),
        sa.Column("request_key", sa.String(128), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("task_key", sa.String(256), nullable=False),
        sa.Column("task_version", sa.Integer(), nullable=False),
        sa.Column("inputs", JSON_TYPE, nullable=False),
        sa.Column("snapshot", JSON_TYPE, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("output", JSON_TYPE),
        sa.Column("error", sa.Text()),
        sa.Column("next_action_at", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("provider", "environment", "request_key", name="uq_sdk_flow_run_request"),
        *timestamps(),
    )
    op.create_index("ix_sdk_flow_ready", "sdk_flow_runs", ["status", "next_action_at"])
    op.create_table(
        "sdk_flow_steps",
        identifier(),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("sdk_flow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_key", sa.String(128), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("rework_count", sa.Integer(), nullable=False),
        sa.Column("output", JSON_TYPE),
        sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("run_id", "step_key", name="uq_sdk_flow_step_key"),
        *timestamps(),
    )
    op.create_table(
        "sdk_flow_attempts",
        identifier(),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("sdk_flow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.Uuid(), sa.ForeignKey("sdk_flow_steps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("inputs", JSON_TYPE, nullable=False),
        sa.Column("output", JSON_TYPE),
        sa.Column("error", sa.Text()),
        sa.UniqueConstraint("step_id", "number", name="uq_sdk_flow_attempt_number"),
        *timestamps(),
    )
    op.create_table(
        "sdk_flow_commands",
        identifier(),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("sdk_flow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("command_key", sa.String(128), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("receipt", JSON_TYPE, nullable=False),
        sa.UniqueConstraint("run_id", "command_key", name="uq_sdk_flow_command_identity"),
        *timestamps(),
    )


def downgrade():
    for table in (
        "sdk_flow_commands",
        "sdk_flow_attempts",
        "sdk_flow_steps",
        "sdk_flow_runs",
        "sdk_flow_releases",
        "sdk_flow_environments",
    ):
        op.drop_table(table)
