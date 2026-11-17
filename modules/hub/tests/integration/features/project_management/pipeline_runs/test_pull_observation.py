"""Run reads expose the PR's last observed Draft status and CI verification without reading GitHub."""

import pytest
from app.features.project_management.projects.errors import ProjectError

from tests.integration.features.project_management.pipeline_runs.test_merge_stage import HEAD, advance
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import github as github
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import run as run
from tests.utils.assertions import assert_status_code

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def read(client, run: dict) -> dict:
    response = await client.get(f"/api/v1/pipeline-runs/{run['id']}")
    assert_status_code(response, 200)
    return response.json()


async def listed(client, run: dict) -> dict:
    response = await client.get("/api/v1/pipeline-runs", params={"project_id": run["project_id"]})
    assert_status_code(response, 200)
    return next(item for item in response.json()["items"] if item["id"] == run["id"])


async def test_a_run_reads_empty_until_its_first_ci_observation(client, run, github):
    assert run["pull_observation"] is None
    assert (await read(client, run))["pull_observation"] is None
    assert (await listed(client, run))["pull_observation"] is None


async def test_draft_wait_records_draft_and_current_head_verification(client, run, github, monkeypatch):
    github.draft = True
    github.has_ci = False
    waiting = await advance(client, run)

    observed = waiting["pull_observation"]
    assert observed["draft"] is True
    assert observed["head_sha"] == HEAD
    assert observed["verification"] == "waiting"
    assert observed["reason"]
    assert observed["observed_at"]

    # Reads return the retained observation; they never ask GitHub.
    respond = github.respond
    reads = []
    monkeypatch.setattr(github, "respond", lambda request: reads.append(request.url.path) or respond(request))
    assert (await read(client, run))["pull_observation"] == observed
    assert (await listed(client, run))["pull_observation"] == observed
    assert reads == []


async def test_recording_does_not_move_the_revision(client, run, github):
    github.draft = True
    waiting = await advance(client, run)
    again = await advance(client, run)

    assert again["revision"] == waiting["revision"]
    assert again["pull_observation"]["observed_at"] >= waiting["pull_observation"]["observed_at"]


async def test_ready_and_failing_ci_replace_the_draft_observation(client, run, github):
    github.draft = True
    github.has_ci = False
    await advance(client, run)

    github.draft = False
    github.has_ci = True
    github.ci_conclusion = "failure"
    github.head_sha = "f" * 40
    repaired = await advance(client, run)

    observed = (await read(client, run))["pull_observation"]
    assert repaired["state"] == "implementing"
    assert (observed["draft"], observed["verification"], observed["head_sha"]) == (False, "failed", "f" * 40)


@pytest.mark.parametrize("run", [{"auto_merge": False}], indirect=True)
async def test_passing_ci_is_recorded_when_merge_policy_pauses(client, run, github):
    paused = await advance(client, run)

    assert paused["state"] == "paused"
    assert (paused["pull_observation"]["draft"], paused["pull_observation"]["verification"]) == (False, "passed")


async def test_draft_found_by_the_merge_recheck_wins(client, run, github, monkeypatch):
    from app.features.project_management.pipelines.github import GitHubActionsReader

    original = GitHubActionsReader.observe_pull
    observations = 0

    async def observe(reader, config, number):
        nonlocal observations
        observations += 1
        if observations == 2:
            github.draft = True
        return await original(reader, config, number)

    monkeypatch.setattr(GitHubActionsReader, "observe_pull", observe)
    waiting = await advance(client, run)

    assert "Waiting for approval" in waiting["pause_reason"]
    assert waiting["pull_observation"]["draft"] is True


async def repairing(client, run, github) -> dict:
    """Fail CI on a new head so the run returns to implementation with a recorded verdict."""
    github.ci_conclusion = "failure"
    github.head_sha = "f" * 40
    repaired = await advance(client, run)
    assert repaired["state"] == "implementing"
    assert repaired["pull_observation"]["verification"] == "failed"
    return repaired


async def test_implementation_read_records_draft_and_keeps_the_head_verdict(client, run, github, monkeypatch):
    repaired = await repairing(client, run, github)

    github.draft = True
    respond = github.respond
    paths = []
    monkeypatch.setattr(github, "respond", lambda request: paths.append(request.url.path) or respond(request))
    observed = await advance(client, run)

    recorded = observed["pull_observation"]
    assert observed["state"] == "implementing"
    assert observed["revision"] == repaired["revision"]
    assert (recorded["head_sha"], recorded["draft"], recorded["verification"]) == ("f" * 40, True, "failed")
    assert recorded["reason"] == repaired["pull_observation"]["reason"]
    assert recorded["observed_at"] > repaired["pull_observation"]["observed_at"]
    # Only the implementation stage's own PR read and reply collection; no workflow or extra PR request.
    assert paths.count("/repos/owner/app/pulls/7") == 1
    assert not any("/actions/" in path for path in paths)


async def test_implementation_read_of_a_new_head_waits_for_verification(client, run, github, monkeypatch):
    from app.features.project_management.pipeline_runs.usecases.ci import CIProgress

    await repairing(client, run, github)

    async def unavailable(*args, **kwargs):
        raise ProjectError(502, "GitHub observation unavailable")

    # Stop the advancement loop at the CI stage so only the implementation read is recorded.
    monkeypatch.setattr(CIProgress, "observe", unavailable)
    github.draft = True
    github.head_sha = "a" * 40
    response = await client.post(f"/api/v1/pipeline-runs/{run['id']}/advance")
    assert response.status_code == 502, response.text

    pushed = await read(client, run)
    recorded = pushed["pull_observation"]
    assert pushed["state"] == "awaiting_ci"
    assert (recorded["head_sha"], recorded["draft"], recorded["verification"]) == ("a" * 40, True, "waiting")
    assert recorded["reason"] == "Awaiting verification"
