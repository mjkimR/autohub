from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.features.execution.tasks.domains.maintenance.history import HistoryRetentionRepository
from app.features.execution.tasks.domains.maintenance.sdd_batches import maintain_batches
from app.features.project_management.projects.models import Project
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService
from app.features.project_management.sdd.activity_claims import settle_individual_claims
from app.features.project_management.sdd.batch_driver import BatchDriver
from app.features.project_management.sdd.batch_models import SddActivityClaim, SddBatch
from app_testing_base import utc_now
from sqlalchemy import select, update
from tests.integration.features.notifications.test_tick_housekeeping import make_run

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_fair_bounded_batch_cursor_survives_failure_and_new_driver_instance(session, monkeypatch):
    ids = []
    for index in range(7):
        project = Project(name=f"Batch project {index}")
        session.add(project)
        await session.flush()
        batch = SddBatch(
            project_id=project.id,
            request_id=uuid4(),
            request_digest="0" * 64,
            actor="user:operator",
            basis={},
            evaluation={},
        )
        session.add(batch)
        await session.flush()
        ids.append(batch.id)
    await session.commit()
    seen = []

    async def tick(self, project_id, batch_id):
        seen.append(batch_id)
        if batch_id == ids[1]:
            raise RuntimeError("isolated per-batch observation failure")

    monkeypatch.setattr(BatchDriver, "tick", tick)
    await maintain_batches(None)
    assert len(seen) == 4
    await maintain_batches(None)
    assert len(seen) == 7 and set(seen) == set(ids)
    await maintain_batches(None)
    assert len(seen) == 11 and seen[7:] == seen[:4]


async def test_unresolved_claim_protects_run_until_final_owner_tombstone(session):
    run = await make_run(session, state="completed")
    claim = SddActivityClaim(
        project_id=run.project_id,
        request_id=uuid4(),
        actor="user:operator",
        request_digest="1" * 64,
        unit="docs/proposals/PROP-demo",
        activity="dev",
        checkpoint={},
        run_id=run.id,
    )
    session.add(claim)
    await session.commit()
    from app.features.project_management.pipeline_runs.models import PipelineRun

    now = utc_now()
    await session.execute(
        update(PipelineRun).where(PipelineRun.id == run.id).values(updated_at=now - timedelta(days=40))
    )
    await session.commit()
    assert await HistoryRetentionRepository().delete_runs(session, before=now - timedelta(days=30), now=now) == 0
    await session.commit()
    await settle_individual_claims(ProjectService(ProjectRepository()))
    await session.refresh(claim)
    assert claim.settled and claim.checkpoint["outcome"]["state"] == "completed"
    assert await HistoryRetentionRepository().delete_runs(session, before=now - timedelta(days=30), now=now) == 1
    await session.commit()
    await session.refresh(claim)
    assert claim.run_id is None and claim.checkpoint["outcome"]["run_id"] == str(run.id)
    assert await session.scalar(select(SddActivityClaim.id).where(SddActivityClaim.id == claim.id)) == claim.id


@pytest.mark.parametrize("batch_state", ["running", "stopped"])
@pytest.mark.parametrize("terminal_state", ["failed", "canceled", "rejected"])
async def test_terminal_owner_tombstone_releases_stopped_batch_without_replacement(
    session, monkeypatch, batch_state, terminal_state
):
    from types import SimpleNamespace
    from typing import cast

    from app.features.project_management.sdd.batch_models import SddBatchMember
    from app.features.project_management.sdd.batch_policy import project_basis
    from app.features.project_management.sdd.batch_usecases import SddBatchUseCase
    from app.features.project_management.sdd.usecases import SddUseCase
    from app_layer_base.core.database.transaction import AsyncTransaction

    run = await make_run(session, state="completed" if terminal_state == "rejected" else terminal_state)
    if terminal_state == "rejected":
        run.sdd_progress = {"unit_status": "rejected"}
    p = await session.get(Project, run.project_id)
    assert p
    batch = SddBatch(
        project_id=p.id,
        request_id=uuid4(),
        request_digest="0" * 64,
        actor="user:operator",
        state=batch_state,
        basis={"project": project_basis(p), "ref": "main"},
        evaluation={},
    )
    session.add(batch)
    await session.flush()
    member = SddBatchMember(
        batch_id=batch.id,
        position=0,
        anchor_id="PROP-demo",
        path="docs/proposals/PROP-demo/proposal.md",
        initial={},
        phase="dev",
        state="admitted",
    )
    session.add(member)
    await session.flush()
    claim = SddActivityClaim(
        project_id=p.id,
        member_id=member.id,
        request_id=uuid4(),
        actor="user:operator",
        request_digest="0" * 64,
        unit="docs/proposals/PROP-demo",
        activity="dev",
        checkpoint={},
        run_id=run.id,
    )
    session.add(claim)
    await session.commit()
    observer = SimpleNamespace(
        get_pull_request=AsyncMock(
            return_value={
                "merged": True,
                "merge_commit_sha": "e" * 40,
                "head": {"ref": run.branch},
                "base": {"ref": "main"},
            }
        )
    )
    driver = BatchDriver(
        SddBatchUseCase(
            ProjectService(ProjectRepository()), cast(SddUseCase, SimpleNamespace(observer=observer, run_use_case=None))
        )
    )
    await driver.tick(p.id, batch.id)
    await session.refresh(batch)
    await session.refresh(member)
    await session.refresh(claim)
    assert member.state == terminal_state and claim.settled
    assert member.outcome is not None
    assert member.outcome["terminal_owner"]["run_id"] == str(run.id)
    assert batch.exclusion is (batch_state != "stopped")
    if batch_state == "running":
        assert batch.state == "attention"
        async with AsyncTransaction() as tx:
            row = await tx.get(SddBatch, batch.id)
            assert row
            row.state = "running"  # Explicit Resume still cannot authorize replacement after terminal failure.
        await driver.tick(p.id, batch.id)
        await session.refresh(batch)
        assert batch.state == "attention"
