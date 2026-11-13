"""Cutover retires authority while retaining exact owner and request evidence."""

from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.features.project_management.pipeline_runs.models import ExecutionAttempt, PipelineRun
from app.features.project_management.sdd.batch_models import SddActivityClaim, SddBatch
from app_testing_base import hours_later
from sqlalchemy import select

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios
from tests.integration.migrations.test_default_ai_catalogs import scripts

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
github = scenarios.github
project = scenarios.project


async def migration(session, direction="upgrade"):
    connection = await session.connection()

    def run(conn):
        with Operations.context(MigrationContext.configure(conn)):
            getattr(scripts().get_revision("c693ea40f322").module, direction)()

    await connection.run_sync(run)
    await session.commit()
    session.expire_all()


async def test_retirement_preserves_evidence_fences_workers_and_requires_acknowledgment(
    client, project, github, session
):
    enrolled = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7, "implemented": True})
    assert enrolled.status_code == 201, enrolled.text
    row = await session.get(PipelineRun, UUID(enrolled.json()["id"]))
    identity = row.id
    row.sdd_snapshot = {"provider": "devkit-spec", "spec_dir": "docs/proposals/PROP-old", "policy": {"retained": True}}
    row.sdd_progress = {"approval": {"actor": "previous-operator"}, "head_sha": scenarios.HEAD}
    row.state = "implementing"
    row.lease_token, row.lease_owner, row.lease_expires_at = uuid4(), "old-worker", hours_later(1)
    attempt = await session.scalar(select(ExecutionAttempt).where(ExecutionAttempt.pipeline_run_id == row.id))
    request_before = dict(attempt.request_snapshot)
    claim = SddActivityClaim(
        project_id=row.project_id,
        request_id=uuid4(),
        actor="old",
        request_digest="old",
        unit="docs/proposals/PROP-old",
        activity="plan",
        checkpoint={"uncertain": True, "initial_sha": scenarios.HEAD, "lease": "old"},
        run_id=row.id,
    )
    batch = SddBatch(
        project_id=row.project_id,
        request_id=uuid4(),
        request_digest="old-batch",
        actor="old",
        basis={"retained": True},
        state="attention",
        exclusion=True,
        detail="Old wait",
    )
    session.add_all([claim, batch])
    await session.commit()
    claim_id, batch_id, attempt_id = claim.id, batch.id, attempt.id
    await migration(session)
    retired = await session.get(PipelineRun, identity)
    assert retired.state == "canceled"
    assert retired.lease_token is None and retired.lease_owner is None and retired.lease_expires_at is None
    assert retired.sdd_progress["approval"] == {"actor": "previous-operator"}
    assert retired.sdd_progress["retirement"]["external_work_unreconciled"] is True
    saved_attempt = await session.get(ExecutionAttempt, attempt_id)
    assert saved_attempt.state == "failed" and saved_attempt.failure_code == "SDD_EXECUTION_RETIRED"
    assert saved_attempt.request_snapshot == request_before
    saved_claim = await session.get(SddActivityClaim, claim_id)
    assert saved_claim.checkpoint["retired"] and saved_claim.checkpoint["lease"] is None
    assert not saved_claim.settled and saved_claim.checkpoint["uncertain"]
    saved_batch = await session.get(SddBatch, batch_id)
    assert saved_batch.state == "stopped" and not saved_batch.exclusion
    assert saved_batch.basis == {"retained": True}
    refused = await client.post(
        f"/api/v1/pipeline-runs/{identity}/resume",
        json={"request_id": str(uuid4()), "expected_revision": retired.revision},
    )
    assert refused.status_code == 410, refused.text
    replacement = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7})
    assert replacement.status_code == 409 and "reconcile" in replacement.text
    before_paths = list(github.paths)
    await migration(session, "downgrade")
    assert (await session.get(PipelineRun, identity)).state == "canceled"
    assert github.paths == before_paths
    history = (await client.get(f"/api/v1/pipeline-runs/{identity}")).json()
    acknowledged = await client.post(
        f"/api/v1/projects/{project['id']}/sdd/runs/{identity}/reconcile",
        json={"request_id": str(uuid4()), "expected_revision": history["revision"], "acknowledge_external_work": True},
    )
    assert acknowledged.status_code == 200, acknowledged.text
    # A direct-Run acknowledgment cannot discard an independent retained claim.
    replacement = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7})
    assert replacement.status_code == 409, replacement.text
    claim_root = f"/api/v1/projects/{project['id']}/sdd/claims/{claim_id}"
    inspected = (await client.get(claim_root)).json()
    reconciled = await client.post(
        claim_root + "/reconcile",
        json={"request_id": str(uuid4()), "expected_checkpoint_digest": inspected["checkpoint_digest"], "acknowledge_external_work": True},
    )
    assert reconciled.status_code == 200 and reconciled.json()["settled"], reconciled.text
    assert (await client.get(f"/api/v1/pipeline-runs/{identity}")).json()["state"] == "canceled"
    replacement = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7})
    assert replacement.status_code == 201, replacement.text


@pytest.mark.parametrize(
    "snapshot", [None, {"execution_version": 2, "provider": "repository-agent", "spec_dir": "docs/proposals/PROP-new"}]
)
async def test_retirement_preserves_current_execution_and_terminal_history(client, project, github, session, snapshot):
    enrolled = (await scenarios.enroll(client, project)).json()
    row = await session.get(PipelineRun, UUID(enrolled["id"]))
    row.sdd_snapshot = snapshot
    await session.commit()
    identity = row.id
    await migration(session)
    assert (await session.get(PipelineRun, identity)).state == "queued"
    row = await session.get(PipelineRun, identity)
    row.state = "completed"
    row.sdd_snapshot = {"provider": "devkit-spec", "spec_dir": "docs/proposals/PROP-old"}
    row.sdd_progress = {"approval": {"actor": "historical"}}
    await session.commit()
    await migration(session)
    row = await session.get(PipelineRun, identity)
    assert row.state == "completed" and row.sdd_progress == {"approval": {"actor": "historical"}}
