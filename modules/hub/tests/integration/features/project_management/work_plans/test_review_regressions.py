from uuid import UUID, uuid4

import pytest
from app.features.ai_catalogs.models import AICatalog
from app.features.project_management.pipeline_runs.models import ExecutionAttempt, PipelineRun
from app.features.project_management.pipelines.github import GitHubObservationError
from app.features.project_management.projects.models import Project
from app.features.project_management.work_plans.github import WorkGitHub
from app.features.project_management.work_plans.models import WorkIssueMirror
from app_layer_base.core.database.transaction import AsyncTransaction
from sqlalchemy import select
from tests.integration.features.project_management.work_plans.test_work_plans import (
    control,
    create,
    due,
    get,
    spec,
)

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.mark.parametrize("revoke", [False, True])
async def test_bad_base_releases_capacity_and_preserves_failure(client, setup_work, session, revoke):
    project, github, worker, _ = setup_work
    # A similarly named branch must not satisfy the exact target lookup.
    github.refs["missing-branch-extra"] = "d" * 40
    async with AsyncTransaction() as tx:
        saved = await tx.get(Project, UUID(project["id"]))
        assert saved is not None
        saved.automation = {**saved.automation, "max_in_flight_runs": 1}
    bad = await create(client, project, spec(base_branch="missing-branch"))
    await worker.advance_project(UUID(project["id"]))
    failed = await get(client, project, bad)
    assert failed["items"][0]["state"] == "preparation_failed"
    assert "Target branch is absent" in failed["items"][0]["detail"]
    assert not github.pulls
    if revoke:
        await control(client, project, failed, "revoke")
    good = await create(client, project)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    actual = await get(client, project, good)
    assert actual["items"][0]["pipeline_run_id"] is not None, actual["items"][0]
    retained = await get(client, project, bad)
    assert retained["items"][0]["state"] == "preparation_failed"
    assert retained["items"][1]["state"] == ("revoked" if revoke else "waiting")
    assert sum(path.endswith("/git/ref/heads/missing-branch") for _, path in github.requests) == 1


@pytest.mark.parametrize("status", [None, 400, 401, 403, 404, 422, 429, 500])
async def test_transient_preparation_failure_keeps_identity_and_reservation(
    client, setup_work, session, monkeypatch, status
):
    project, github, worker, _ = setup_work
    plan = await create(client, project)

    async def unavailable(*args):
        raise GitHubObservationError("Preparation not confirmed", status)

    with monkeypatch.context() as patch:
        patch.setattr(WorkGitHub, "prepare", unavailable)
        await worker.advance_project(UUID(project["id"]))
    first = (await get(client, project, plan))["items"][0]
    assert first["state"] == "preparing"
    other = await create(client, project)
    await worker.advance_project(UUID(project["id"]))
    assert (await get(client, project, other))["items"][0]["started_at"] is None
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    recovered = (await get(client, project, plan))["items"][0]
    assert recovered["pipeline_run_id"]
    assert recovered["started_at"] == first["started_at"]
    assert len(github.pulls) == 1


@pytest.mark.parametrize("status", [401, 403, 422, 429])
async def test_response_loss_then_lookup_failure_does_not_duplicate_issue(client, setup_work, session, status):
    project, github, _, sync = setup_work
    plan = await create(client, project)
    # Restrict this probe to the Plan mirror, isolating retries of the same entity.
    async with AsyncTransaction() as tx:
        others = list(await tx.scalars(select(WorkIssueMirror).where(WorkIssueMirror.entity_id != UUID(plan["id"]))))
        for row in others:
            row.synced_digest = row.digest
    github.lose_issue_response = True
    await sync.execute(limit=1)
    assert len(github.issues) == 1
    github.issue_failure_status = status
    github.fail_issues = True
    await due(session)
    await sync.execute(limit=1)
    github.fail_issues = False
    await due(session)
    await sync.execute(limit=1)
    assert len(github.issues) == 1, list(github.issues.values())


@pytest.mark.parametrize(
    "run_state,attempt_state",
    [("queued", "planned"), ("dispatching", "planned"), ("dispatching", "dispatching"), ("implementing", "running")],
)
async def test_each_run_reserves_one_slot(client, setup_work, session, run_state, attempt_state):
    project, _, worker, _ = setup_work
    plan = await create(client, project)
    await worker.advance_project(UUID(project["id"]))
    state = await get(client, project, plan)
    async with AsyncTransaction() as tx:
        run = await tx.get(PipelineRun, UUID(state["items"][0]["pipeline_run_id"]))
        assert run is not None
        catalog = await tx.get(AICatalog, run.ai_catalog_id)
        assert catalog is not None
        catalog.configured_concurrency = 2
        run.state = run_state
        tx.add(
            ExecutionAttempt(
                pipeline_run_id=run.id,
                attempt_number=1,
                epoch=1,
                kind="implementation",
                state=attempt_state,
                request_snapshot={},
                request_digest="a" * 64,
                idempotency_key=uuid4(),
            )
        )
    good = await create(client, project)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    actual = await get(client, project, good)
    assert actual["items"][0]["pipeline_run_id"] is not None, actual["items"][0]

    # Both slots are now occupied; admitting a third would overrun the limit.
    third = await create(client, project)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert (await get(client, project, third))["items"][0]["pipeline_run_id"] is None
