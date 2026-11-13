"""Retire embedded SDD authority without deleting execution history."""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c693ea40f322"
down_revision = "b582df39e211"
branch_labels = None
depends_on = None

REASON = "Native SDD evaluation was retired; inspect external work before registering replacement work"
FINAL = ("completed", "failed", "canceled")


def upgrade():
    connection = op.get_bind()
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    runs = sa.table(
        "pipeline_runs", sa.column("id", sa.Uuid()), sa.column("state", sa.String()),
        sa.column("sdd_snapshot", json_type), sa.column("sdd_progress", json_type),
        sa.column("revision", sa.Integer()), sa.column("epoch", sa.Integer()),
        sa.column("pause_reason", sa.Text()), sa.column("lease_owner", sa.String()),
        sa.column("lease_token", sa.Uuid()), sa.column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.column("next_action_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    attempts = sa.table(
        "execution_attempts", sa.column("pipeline_run_id", sa.Uuid()), sa.column("state", sa.String()),
        sa.column("failure_code", sa.String()), sa.column("failure_detail", sa.Text()),
        sa.column("finished_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    retired_ids = []
    for row in connection.execute(sa.select(runs).where(runs.c.sdd_snapshot.is_not(None))).mappings():
        snapshot = row["sdd_snapshot"] or {}
        if not snapshot or snapshot.get("execution_version") == 2 or row["state"] in FINAL:
            continue
        retired_ids.append(row["id"])
        progress = {
            **(row["sdd_progress"] or {}),
            "retirement": {"reason": REASON, "external_work_unreconciled": True},
        }
        connection.execute(
            runs.update().where(runs.c.id == row["id"]).values(
                state="canceled", pause_reason=REASON, revision=row["revision"] + 1,
                epoch=row["epoch"] + 1, sdd_progress=progress, lease_owner=None,
                lease_token=None, lease_expires_at=None, next_action_at=None, updated_at=now,
            )
        )
    if retired_ids:
        connection.execute(
            attempts.update().where(
                attempts.c.pipeline_run_id.in_(retired_ids),
                attempts.c.state.in_(("planned", "dispatching", "running", "suspended")),
            ).values(state="failed", failure_code="SDD_EXECUTION_RETIRED", failure_detail=REASON,
                     finished_at=now, updated_at=now)
        )
    batches = sa.table(
        "sdd_batches", sa.column("id", sa.Uuid()), sa.column("state", sa.String()),
        sa.column("revision", sa.Integer()), sa.column("exclusion", sa.Boolean()),
        sa.column("detail", sa.String()), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    connection.execute(
        batches.update().where(batches.c.exclusion.is_(True)).values(
            state="stopped", exclusion=False, revision=batches.c.revision + 1,
            detail=REASON, updated_at=now,
        )
    )
    claims = sa.table(
        "sdd_activity_claims", sa.column("id", sa.Uuid()), sa.column("checkpoint", json_type),
        sa.column("settled", sa.Boolean()), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    for row in connection.execute(sa.select(claims)).mappings():
        checkpoint = row["checkpoint"] or {}
        if checkpoint.get("execution_version") == 2:
            continue
        connection.execute(
            claims.update().where(claims.c.id == row["id"]).values(
                checkpoint={**checkpoint, "retired": True, "lease": None, "lease_expires_at": None},
                updated_at=now,
            )
        )
    # Discovery is a rebuildable projection, unlike the retained decision receipts.
    decisions = sa.table("run_decision_entries", sa.column("kind", sa.String()))
    connection.execute(decisions.delete().where(decisions.c.kind.like("native-%")))
    flows = sa.table(
        "sdk_flow_runs", sa.column("id", sa.Uuid()), sa.column("status", sa.String()),
        sa.column("snapshot", json_type), sa.column("revision", sa.Integer()),
        sa.column("lease_token", sa.Uuid()), sa.column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.column("next_action_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    for row in connection.execute(sa.select(flows).where(flows.c.status.in_(("queued", "running", "waiting", "canceling")))).mappings():
        bindings = (row["snapshot"] or {}).get("bindings") or {}
        if any(str(binding.get("target", "")).startswith(("autohub.sdd:", "autohub.pr_delivery:")) for binding in bindings.values()):
            connection.execute(
                flows.update().where(flows.c.id == row["id"]).values(
                    revision=row["revision"] + 1, lease_token=None, lease_expires_at=None,
                    next_action_at=now, updated_at=now,
                )
            )


def downgrade():
    # Reverting code never restores a retired grant or replays an external effect.
    pass
