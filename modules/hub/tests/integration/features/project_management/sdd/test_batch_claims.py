from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService
from app.features.project_management.sdd import activities
from app.features.project_management.sdd.activity_claims import ActivityClaims
from app.features.project_management.sdd.batch_models import SddActivityClaim
from app.features.project_management.sdd.schemas import StartActivityRequest
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time

from tests.integration.features.project_management.pipeline_runs import test_merge_stage as merge
from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

github = merge.github
project = scenarios.project
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def reserve(project, *, projects=None):
    projects = projects or ProjectService(ProjectRepository())
    claims = ActivityClaims(projects, None, AsyncMock())
    async with AsyncTransaction() as session:
        row = await projects.get(session, UUID(project["id"]), lock=True)
        claim = await claims.reserve(
            session, row, "dev", "demo", StartActivityRequest(request_id=uuid4()), "user:operator"
        )
        claim_id = claim.id
    return claims, claim_id


async def test_proven_pre_effect_refusal_is_replayable_but_releases_fresh_request(project, monkeypatch):
    claims, claim_id = await reserve(project)
    start = AsyncMock(side_effect=ProjectError(409, "Development needs an accepted proposal"))
    monkeypatch.setattr(activities.ActivityStarter, "start", start)
    with pytest.raises(ProjectError):
        await claims.execute(UUID(project["id"]), claim_id)
    async with AsyncTransaction() as session:
        row = await session.get(SddActivityClaim, claim_id)
        assert row and row.settled and row.checkpoint["refusal"]["status"] == 409
    # Same original command stays a refusal; a fresh explicitly reviewed command may reserve.
    with pytest.raises(ProjectError):
        await claims.execute(UUID(project["id"]), claim_id)
    assert start.await_count == 1
    _, next_id = await reserve(project)
    assert next_id != claim_id


@pytest.mark.parametrize("where", ["checkpoint", "settlement"])
async def test_expired_worker_cannot_checkpoint_or_settle(project, monkeypatch, where):
    claims, claim_id = await reserve(project)

    async def start(*args, checkpoint, **kwargs):
        async with AsyncTransaction() as session:
            row = await session.get(SddActivityClaim, claim_id)
            assert row
            row.checkpoint = {
                **row.checkpoint,
                "lease_expires_at": (get_current_utc_time() - timedelta(seconds=1)).isoformat(),
            }
        if where == "checkpoint":
            await checkpoint(initial_sha="b" * 40)
        return type("Result", (), {"id": uuid4()})()

    monkeypatch.setattr(activities.ActivityStarter, "start", start)
    with pytest.raises(ProjectError):
        await claims.execute(UUID(project["id"]), claim_id)
    async with AsyncTransaction() as session:
        row = await session.get(SddActivityClaim, claim_id)
        assert row and row.run_id is None and "initial_sha" not in row.checkpoint
