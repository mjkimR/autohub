"""Timestamp behavior through real run and connection-test owner methods."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from app.features.execution.tasks.domains.maintenance.history import HistoryRetentionRepository
from app.features.project_management.connection_tests.repos import ConnectionTestRepository
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.queries import PipelineRunQueries

from tests.integration.common.test_timestamps import OLD, utc
from tests.integration.features.notifications.test_tick_housekeeping import make_run
from tests.integration.features.project_management.owed_items import test_owed_items as owed

project = owed.project
github = owed.github
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_run_leases_notification_and_rotation(session, clock):
    repo = PipelineRunRepository()
    first = await make_run(session, state="implementing")
    # The observing population exceeds the bounded selection of one.
    second = PipelineRun(
        project_id=first.project_id,
        ai_catalog_id=first.ai_catalog_id,
        project_revision=1,
        github_repository=first.github_repository,
        pull_number=43,
        pull_url=first.pull_url + "3",
        pull_snapshot={},
        branch="second",
        state="implementing",
        created_at=OLD,
        updated_at=OLD,
    )
    session.add(second)
    await session.commit()
    original = utc(second.updated_at)
    token = uuid4()
    assert await repo.acquire_lease(
        session, second.id, owner="clock", token=token, now=clock[0], expires_at=clock[0] + timedelta(minutes=2)
    )
    await session.refresh(second)
    assert utc(second.updated_at) == original
    assert await repo.renew_lease(
        session, second.id, owner="clock", token=token, now=clock[0], expires_at=clock[0] + timedelta(minutes=3)
    )
    await repo.mark_stop_announced(session, second.id, second.revision)
    await session.refresh(second)
    assert utc(second.updated_at) == original
    assert (
        await repo.renew_lease(
            session, second.id, owner="wrong", token=token, now=clock[0], expires_at=clock[0] + timedelta(minutes=3)
        )
        is None
    )
    assert (await repo.list_active(session, first.project_id, limit=1))[0].id == second.id
    second_id = second.id
    session.expire(second)
    await repo.release_lease(session, second_id, owner="clock", token=token, now=clock[0])
    await session.refresh(second)
    assert utc(second.updated_at) == clock[0]
    assert (await repo.list_active(session, first.project_id, limit=1))[0].id == first.id


async def test_connection_claim_preserves_and_finish_uses_explicit_clock(client, project, session, clock):
    test = await owed.connection_test(session, project)
    await session.commit()
    original = utc(test.updated_at)
    repo = ConnectionTestRepository()
    claimed = await repo.claim(session, test.id)
    assert claimed is not None
    row, token = claimed
    assert utc(row.updated_at) == original
    row.detail = "Owner step completed"
    assert await repo.finish_step(session, row, token)
    await session.refresh(row)
    assert utc(row.updated_at) == clock[0]


@pytest.mark.parametrize("terminal", ["canceled", "closed", "failed"])
async def test_operator_terminal_and_failed_owed_read_use_maintained_time(
    client, project, github, session, clock, terminal
):
    # Old timestamps are INSERT evidence, never an assigned expected UPDATE result.
    initial = await owed.enroll(client, github, project, 7)
    run = await session.get(PipelineRun, UUID(initial["id"]), populate_existing=True)
    created = utc(run.created_at)
    if terminal == "canceled":
        response = await client.post(f"/api/v1/pipeline-runs/{run.id}/cancel")
        assert response.status_code == 200, response.text
    elif terminal == "closed":
        from app.features.project_management.pipeline_runs.usecases.transitions import finish_closed_pull

        await finish_closed_pull(PipelineRunRepository(), session, run, {"merged": False, "state": "closed"}, clock[0])
        await session.commit()
    else:
        from app.features.project_management.pipeline_runs.models import ExecutionAttempt

        run.state = "implementing"
        attempt = ExecutionAttempt(
            pipeline_run_id=run.id,
            attempt_number=1,
            kind="implementation",
            state="running",
            request_snapshot={},
            request_digest="a" * 64,
            idempotency_key=uuid4(),
        )
        session.add(attempt)
        await session.commit()
        clock[0] += timedelta(hours=1)
        response = await client.post(
            f"/api/v1/pipeline-runs/{run.id}/attempts/{attempt.id}/complete", json={"status": "failed"}
        )
        assert response.status_code == 200, response.text
    await session.refresh(run)
    assert utc(run.updated_at) == clock[0]
    assert utc(run.created_at) == created
    summary = await PipelineRunQueries(PipelineRunRepository()).list_attempts(run.id)
    assert summary.summary.finished_at == clock[0]
    assert (
        await HistoryRetentionRepository().delete_runs(
            session, before=clock[0] - timedelta(days=30), now=clock[0], limit=50
        )
        == 0
    )
    rows = await owed.items(client)
    matches = [r for r in rows if r["subject"]["id"] == str(run.id)]
    if terminal == "failed":
        assert len(matches) == 1
        assert matches[0]["waiting_since"] == clock[0].isoformat().replace("+00:00", "Z")


async def test_pause_is_mixed_business_write_and_rejected_cancel_preserves(client, project, github, session, clock):
    initial = await owed.enroll(client, github, project, 7)
    rid = initial["id"]
    response = await client.post(f"/api/v1/pipeline-runs/{rid}/pause")
    assert response.status_code == 200, response.text
    row = await session.get(PipelineRun, UUID(rid), populate_existing=True)
    assert utc(row.updated_at) == clock[0]
    stopped = [r for r in await owed.items(client) if r["kind"] == "stopped-run"]
    assert stopped[0]["waiting_since"] == clock[0].isoformat().replace("+00:00", "Z")
    assert (await client.post(f"/api/v1/pipeline-runs/{rid}/cancel")).status_code == 200
    clock[0] += timedelta(days=1)
    assert (await client.post(f"/api/v1/pipeline-runs/{rid}/cancel")).status_code == 422
    await session.refresh(row)
    assert utc(row.updated_at) == clock[0] - timedelta(days=1)
