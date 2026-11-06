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


async def test_enrollment_commit_response_loss_recovers_atomic_exact_run(client, project, github, monkeypatch):
    from app.features.project_management.pipeline_runs.models import PipelineRun
    from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
    from app.features.project_management.pipeline_runs.schemas import EnrollPullRequest
    from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
    from app.features.project_management.pipelines.services import PipelineObservationService
    from app.features.project_management.sdd.services import SddService
    from sqlalchemy import func, select

    from tests.integration.features.project_management.sdd.test_native import evidence

    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    original_pull = github.pull
    monkeypatch.setattr(
        github, "pull", lambda: {**original_pull(), "head": {**original_pull()["head"], "ref": "dev-demo"}}
    )
    github.draft = True
    unit = "docs/proposals/PROP-demo"

    async def inspect(self, repository, spec_dir, pull, token, **kwargs):
        value = evidence(pull["head"]["sha"], pull["base"]["sha"])
        value["snapshot"]["spec_dir"] = unit
        value["unit_status"] = "accepted"
        return value

    monkeypatch.setattr(SddService, "inspect", inspect)
    projects = ProjectService(ProjectRepository())
    observer = PipelineObservationService(AsyncMock(return_value="token"))
    runs = PipelineRunUseCase(PipelineRunRepository(), projects, observer)
    claims = ActivityClaims(projects, observer, runs)
    async with AsyncTransaction() as tx:
        p = await projects.get(tx, UUID(project["id"]), lock=True)
        claim = await claims.reserve(tx, p, "dev", "demo", StartActivityRequest(request_id=uuid4()), "user:operator")
        claim_id = claim.id
    starts = 0

    async def start(self, p, activity, slug, request, actor, *, checkpoint, admission=None, **kwargs):
        nonlocal starts
        starts += 1
        await checkpoint(
            initial_sha=github.pull()["head"]["sha"],
            branch="dev-demo",
            pull_number=7,
            enrollment_request=EnrollPullRequest(pull_number=7, spec_dir=unit, handoff=True).model_dump(mode="json"),
        )
        result = await runs.enroll(
            p.id,
            EnrollPullRequest(pull_number=7, spec_dir=unit, handoff=True),
            **({"admission": admission} if admission else {}),
        )
        assert result.id
        raise TimeoutError("Enrollment committed; response lost before outer claim settlement")

    monkeypatch.setattr(activities.ActivityStarter, "start", start)
    with pytest.raises(TimeoutError):
        await claims.execute(UUID(project["id"]), claim_id)
    async with AsyncTransaction() as tx:
        row = await tx.get(SddActivityClaim, claim_id)
        assert row and row.run_id is not None
        assert row.checkpoint["uncertain"] and row.checkpoint["uncertainty_observed_at"]
        run_id = row.run_id
    recovered = await claims.execute(UUID(project["id"]), claim_id)
    assert recovered.id == run_id and starts == 1
    async with AsyncTransaction() as tx:
        assert (
            await tx.scalar(
                select(func.count()).select_from(PipelineRun).where(PipelineRun.project_id == UUID(project["id"]))
            )
            == 1
        )

    from datetime import timedelta

    from app.features.execution.tasks.domains.maintenance.history import HistoryRetentionRepository
    from app.features.project_management.sdd.activity_claims import settle_individual_claims
    from sqlalchemy import update

    now = get_current_utc_time()
    async with AsyncTransaction() as tx:
        await tx.execute(
            update(PipelineRun)
            .where(PipelineRun.id == run_id)
            .values(state="completed", updated_at=now - timedelta(days=40))
        )
    await settle_individual_claims(projects)
    async with AsyncTransaction() as tx:
        assert await HistoryRetentionRepository().delete_runs(tx, before=now - timedelta(days=30), now=now) == 1
    with pytest.raises(ProjectError):
        await claims.execute(UUID(project["id"]), claim_id)
    assert starts == 1, "Retired settled original receipt must never re-enter remote admission"
