"""Resume reconciles delivered implementation across a project-settings interruption."""

from uuid import UUID, uuid4

import pytest
from app.features.project_management.pipeline_runs.models import ExecutionAttempt, ExecutionDelivery, PipelineRun
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.pipeline_runs.schemas import ImplementationRequest
from app.features.project_management.projects.models import ProjectConnection
from app_testing_base import utc_now
from sqlalchemy import update

from tests.integration.features.project_management.pipeline_runs.test_merge_stage import HEAD, MergeScenario
from tests.integration.features.project_management.pipeline_runs.test_pipeline_runs_api import (
    github as github,
)
from tests.integration.features.project_management.pipeline_runs.test_pipeline_runs_api import (
    mention_github as mention_github,
)
from tests.integration.features.project_management.pipeline_runs.test_pipeline_runs_api import (
    prepare_run,
    resume,
)
from tests.integration.features.project_management.pipeline_runs.test_pipeline_runs_api import (
    project as project,
)
from tests.utils.assertions import assert_status_code

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.fixture
async def interrupted(client, project, github, mention_github, session, request):
    github.pulls[7]["head"]["sha"] = "a" * 40
    run, original = await prepare_run(client, project)
    root = f"/api/v1/pipeline-runs/{run['id']}"
    assert (await client.post(f"{root}/advance")).json()["state"] == "implementing"
    github.pulls[7]["head"]["sha"] = HEAD
    if getattr(request, "param", False):
        assert (await client.post(f"{root}/advance")).json()["state"] == "awaiting_ci"
    await session.execute(
        update(ProjectConnection)
        .where(ProjectConnection.id == UUID(project["id"]))
        .values(revision=ProjectConnection.revision + 1)
    )
    await session.commit()
    assert (await client.post(f"{root}/advance")).json()["state"] == "blocked"
    return root, original


@pytest.mark.parametrize("retries", [0, 1, 2])
@pytest.mark.parametrize("interrupted", [False, True], indirect=True)
@pytest.mark.parametrize("ci", ["success", "failure"])
async def test_resume_recovers_original_push_after_project_change(
    client, interrupted, github, mention_github, session, retries, monkeypatch, ci
):
    root, original = interrupted
    # Reconstruct attempts already replayed by the old resume behavior. Every replay starts
    # at the implemented head and ends without another push; the original evidence remains.
    for number in range(2, retries + 2):
        key = uuid4()
        request = ImplementationRequest.model_validate(original["request_snapshot"])
        snapshot = request.model_copy(
            update={
                "correlation_marker": f"hub-attempt:{key}",
                "pull_request": request.pull_request.model_copy(update={"head_sha": HEAD}),
            }
        ).model_dump(mode="json")
        attempt = ExecutionAttempt(
            pipeline_run_id=UUID(original["pipeline_run_id"]),
            attempt_number=number,
            epoch=number,
            kind="implementation",
            state="running" if number == retries + 1 else "failed",
            failure_code=None if number == retries + 1 else "USER_RESUMED",
            request_snapshot=snapshot,
            request_digest=request_digest(snapshot),
            idempotency_key=key,
        )
        session.add(attempt)
        await session.flush()
        session.add(
            ExecutionDelivery(execution_attempt_id=attempt.id, delivery_number=1, cause="resume", posted_at=utc_now())
        )
    if retries:
        await session.execute(
            update(PipelineRun)
            .where(PipelineRun.id == UUID(original["pipeline_run_id"]))
            .values(epoch=retries + 1, pause_reason="Codex replied without pushing")
        )
    await session.commit()

    command = {
        "request_id": str(uuid4()),
        "expected_revision": (await client.get(root)).json()["revision"],
    }
    resumed = await client.post(f"{root}/resume", json=command)

    assert_status_code(resumed, 200)
    assert resumed.json()["state"] == "awaiting_ci"
    assert resumed.json()["pause_reason"] is None
    attempts = (await client.get(f"{root}/attempts")).json()["items"]
    assert attempts[0]["state"] == "failed"
    assert attempts[0]["failure_code"] == "PROJECT_CHANGED"
    assert attempts[-1]["state"] == "running"
    assert len(mention_github) == 1
    replayed = await client.post(f"{root}/resume", json=command)
    assert_status_code(replayed, 200)
    assert replayed.json()["revision"] == resumed.json()["revision"]
    assert len((await client.get(f"{root}/attempts")).json()["items"]) == len(attempts)
    if not retries:
        assert attempts[-1]["external_status"] == "implemented-externally"
        assert (await client.get(f"{root}/attempts/{attempts[-1]['id']}/deliveries")).json() == []
        assert_status_code(await client.post(f"{root}/pause"), 200)
        assert (await resume(client, root)).json()["state"] == "awaiting_ci"
        assert len((await client.get(f"{root}/attempts")).json()["items"]) == len(attempts)

    # Recovery must retain a CI owner for both completion and repair under the current settings.
    scenario = MergeScenario()
    scenario.ci_conclusion = ci
    monkeypatch.setattr(github, "respond", scenario.respond)
    advanced = await client.post(f"{root}/advance")
    assert_status_code(advanced, 200)
    assert advanced.json()["state"] == ("implementing" if ci == "failure" else "completed")
    attempts = (await client.get(f"{root}/attempts")).json()["items"]
    if ci == "failure":
        assert attempts[-1]["kind"] == "ci-fix"
        assert attempts[-1]["request_snapshot"]["pull_request"]["head_sha"] == HEAD
    else:
        assert attempts[-1]["state"] == "completed"
        assert scenario.merge_requests == 1


@pytest.mark.parametrize("change", ["no-push", "undelivered", "instructions", "ci-fix", "conflict-fix", "failure"])
async def test_resume_does_not_borrow_unrelated_or_missing_push_evidence(client, interrupted, github, session, change):
    root, original = interrupted
    if change == "no-push":
        github.pulls[7]["head"]["sha"] = "a" * 40
    elif change == "undelivered":
        await session.execute(
            update(ExecutionDelivery)
            .where(ExecutionDelivery.execution_attempt_id == UUID(original["id"]))
            .values(posted_at=None)
        )
    else:
        key = uuid4()
        request = ImplementationRequest.model_validate(original["request_snapshot"])
        snapshot = request.model_copy(
            update={
                "correlation_marker": f"hub-attempt:{key}",
                "pull_request": request.pull_request.model_copy(update={"head_sha": HEAD}),
                "instructions": request.instructions + "\nNew operator answer"
                if change == "instructions"
                else request.instructions,
                "kind": change if change in ("ci-fix", "conflict-fix") else "implementation",
            }
        ).model_dump(mode="json")
        session.add(
            ExecutionAttempt(
                pipeline_run_id=UUID(original["pipeline_run_id"]),
                attempt_number=2,
                epoch=2,
                kind=snapshot["kind"],
                state="failed" if change == "failure" else "running",
                failure_code="CI_FAILED" if change == "failure" else None,
                request_snapshot=snapshot,
                request_digest=request_digest(snapshot),
                idempotency_key=key,
            )
        )
    await session.commit()

    resumed = await resume(client, root)

    assert_status_code(resumed, 200)
    assert resumed.json()["state"] == "dispatching"
