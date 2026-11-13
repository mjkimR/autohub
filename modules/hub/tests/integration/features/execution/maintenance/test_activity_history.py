from datetime import timedelta
from uuid import uuid4

import pytest
from app.features.execution.tasks.domains.maintenance.history import HistoryRetentionRepository
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService
from app.features.project_management.sdd.activity_claims import settle_individual_claims
from app.features.project_management.sdd.batch_models import SddActivityClaim
from app_testing_base import utc_now
from sqlalchemy import select, update
from tests.integration.features.notifications.test_tick_housekeeping import make_run

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_unresolved_claim_protects_run_until_final_owner_tombstone(session):
    run = await make_run(session, state="completed")
    claim = SddActivityClaim(
        project_id=run.project_id,
        request_id=uuid4(),
        actor="user:operator",
        request_digest="1" * 64,
        unit="docs/proposals/PROP-demo",
        activity="dev",
        checkpoint={"execution_version": 2},
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
