"""The merge stage: what Hub does once CI passed, by GitHub's own verdict on the pull request."""

import httpx
import pytest
from app.features.project_management.pipelines import services
from app.features.project_management.pipelines.github import (
    GitHubActionsReader,
    GitHubObservationError,
    github_http_error,
)

from tests.utils.assertions import assert_status_code

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
HEAD = "c" * 40
BASE = "d" * 40
ROOT = "/repos/owner/app"


class MergeScenario:
    def __init__(self) -> None:
        self.mergeable_state: str | None = "clean"
        self.draft = False
        self.ci_conclusion = "success"
        self.has_ci = True
        # The state GitHub reports once a merge was refused; defaults to the state before it.
        self.state_after_refusal: str | None = None
        self.merge_response = httpx.Response(200, json={"merged": True, "sha": "e" * 40})
        self.merge_requests = 0

    def pull(self) -> dict:
        return {
            "number": 7,
            "state": "open",
            "draft": self.draft,
            "html_url": "https://github.com/owner/app/pull/7",
            "title": "Add feature",
            "body": "Implement the health endpoint.",
            "head": {"ref": "feature/7", "sha": HEAD, "repo": {"full_name": "owner/app"}},
            "base": {"ref": "main", "sha": BASE, "repo": {"full_name": "owner/app"}},
            "mergeable_state": self.mergeable_state,
        }

    def respond(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix(ROOT)
        workflow_run = {
            "id": 1,
            "run_number": 1,
            "run_attempt": 1,
            "head_sha": HEAD,
            "event": "pull_request",
            "path": ".github/workflows/ci.yml",
            "head_repository": {"full_name": "owner/app"},
            "pull_requests": [{"number": 7, "head": {"sha": HEAD}, "base": {"sha": BASE}}],
            "status": "completed",
            "conclusion": self.ci_conclusion,
            "html_url": "https://github.com/owner/app/actions/runs/1",
            "updated_at": "2026-09-21T00:00:00Z",
        }
        if request.method == "PUT" and path == "/pulls/7/merge":
            self.merge_requests += 1
            if self.merge_response.status_code != 200 and self.state_after_refusal is not None:
                self.mergeable_state = self.state_after_refusal
            return self.merge_response
        assert request.method == "GET", f"Unexpected GitHub write: {request.method} {path}"
        if path == "/pulls/7":
            return httpx.Response(200, json=self.pull())
        if path == "/actions/workflows/ci.yml/runs":
            runs = [workflow_run] if self.has_ci else []
            return httpx.Response(200, json={"total_count": len(runs), "workflow_runs": runs})
        if path == "/actions/runs/1/jobs":
            job = {"id": 1, "name": "lint", "status": "completed", "conclusion": self.ci_conclusion, "html_url": None}
            return httpx.Response(200, json={"total_count": 1, "jobs": [job]})
        if path == "/actions/runs/1":
            return httpx.Response(200, json=workflow_run)
        if path == "/actions/jobs/1/logs":
            return httpx.Response(200, text="lint failed")
        raise AssertionError(f"Unexpected GitHub request: {path}")


@pytest.fixture
def github(monkeypatch) -> MergeScenario:
    scenario = MergeScenario()
    monkeypatch.setattr(
        services,
        "create_github_client",
        lambda token: httpx.AsyncClient(
            base_url="https://api.github.com", transport=httpx.MockTransport(scenario.respond)
        ),
    )
    return scenario


@pytest.fixture
async def run(client, github, request) -> dict:
    connector = await client.post(
        "/api/v1/connectors",
        json={"name": "github-account", "provider": "github", "credentials": {"token": "github-test-token"}},
    )
    assert_status_code(connector, 201)
    project = await client.post(
        "/api/v1/projects",
        json={
            "name": "Application",
            "repository": "owner/app",
            "github_connector_id": connector.json()["id"],
            "verification": {"workflow": "ci.yml", "required_jobs": ["lint"], "event": "pull_request"},
            "automation": getattr(request, "param", {}),
        },
    )
    assert_status_code(project, 201)
    enrolled = await client.post(
        f"/api/v1/projects/{project.json()['id']}/runs", json={"pull_number": 7, "implemented": True}
    )
    assert_status_code(enrolled, 201)
    return enrolled.json()


async def advance(client, run: dict) -> dict:
    response = await client.post(f"/api/v1/pipeline-runs/{run['id']}/advance")
    assert_status_code(response, 200)
    return response.json()


async def attempt_kinds(client, run: dict) -> list[str]:
    attempts = await client.get(f"/api/v1/pipeline-runs/{run['id']}/attempts")
    return [item["kind"] for item in attempts.json()["items"]]


async def test_a_clean_pull_request_is_merged(client, run, github):
    advanced = await advance(client, run)

    assert (advanced["state"], advanced["pause_reason"], github.merge_requests) == ("completed", None, 1)


@pytest.mark.parametrize("mergeable_state", ["clean", "blocked", "dirty", None])
@pytest.mark.parametrize("ci", ["success", "skipped", "missing"])
async def test_draft_waits_for_ready_approval_then_required_ci(client, run, github, mergeable_state, ci):
    github.draft = True
    github.mergeable_state = mergeable_state
    github.has_ci = ci != "missing"
    github.ci_conclusion = ci

    waiting = await advance(client, run)
    again = await advance(client, run)
    assert waiting["state"] == "awaiting_ci"
    assert "Waiting for approval" in waiting["pause_reason"]
    assert waiting["next_action_at"] is not None
    assert again["revision"] == waiting["revision"]
    assert github.merge_requests == 0
    assert await attempt_kinds(client, run) == ["implementation"]

    github.draft = False
    github.mergeable_state = "clean"
    github.has_ci = False
    verifying = await advance(client, run)
    assert verifying["state"] == "awaiting_ci"
    assert verifying["pause_reason"] is None
    assert github.merge_requests == 0

    github.has_ci = True
    github.ci_conclusion = "success"
    merged = await advance(client, run)
    assert (merged["state"], merged["pause_reason"], github.merge_requests) == ("completed", None, 1)


async def test_returning_to_draft_during_merge_recheck_revokes_approval(client, run, github, monkeypatch):
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
    assert waiting["state"] == "awaiting_ci"
    assert "Waiting for approval" in waiting["pause_reason"]
    assert github.merge_requests == 0


async def test_draft_still_allows_failed_ci_to_be_fixed(client, run, github):
    github.draft = True
    github.ci_conclusion = "failure"
    advanced = await advance(client, run)
    assert advanced["state"] == "dispatching"
    assert github.merge_requests == 0
    assert await attempt_kinds(client, run) == ["implementation", "ci-fix"]


@pytest.mark.parametrize("run", [{"auto_merge": False}], indirect=True)
async def test_ready_approval_does_not_override_disabled_auto_merge(client, run, github):
    github.draft = True
    github.has_ci = False
    waiting = await advance(client, run)
    assert "Waiting for approval" in waiting["pause_reason"]
    assert "must be enabled" in waiting["pause_reason"]

    github.draft = False
    github.has_ci = True
    ready = await advance(client, run)
    assert ready["state"] == "paused"
    assert "automatic merge is disabled" in ready["pause_reason"]
    assert github.merge_requests == 0
    assert await attempt_kinds(client, run) == ["implementation"]


@pytest.mark.parametrize("status", [405, 409])
async def test_draft_conversion_after_recheck_waits_without_a_conflict_fix(client, run, github, monkeypatch, status):
    respond = github.respond

    def convert_before_merge(request):
        if request.method == "PUT":
            github.draft = True
            github.mergeable_state = "dirty"
            github.merge_response = httpx.Response(status, json={"message": "Pull request is a draft"})
        return respond(request)

    monkeypatch.setattr(github, "respond", convert_before_merge)
    waiting = await advance(client, run)
    assert waiting["state"] == "awaiting_ci"
    assert "Waiting for approval" in waiting["pause_reason"]
    assert github.merge_requests == 1
    assert await attempt_kinds(client, run) == ["implementation"]


@pytest.mark.parametrize(("mergeable_state", "said"), [("blocked", "repository rule"), ("draft", "is a draft")])
async def test_a_merge_waiting_for_a_person_asks_nothing_of_the_agent(client, run, github, mergeable_state, said):
    github.mergeable_state = mergeable_state

    first = await advance(client, run)
    second = await advance(client, run)

    assert first["state"] == "awaiting_ci" and said in first["pause_reason"]
    assert first["next_action_at"] is not None
    # The reason is news once: a later look at the same block does not move the revision (or send another notice).
    assert second["revision"] == first["revision"]
    assert github.merge_requests == 0
    assert await attempt_kinds(client, run) == ["implementation"]

    github.mergeable_state = "clean"
    merged = await advance(client, run)
    assert (merged["state"], merged["pause_reason"]) == ("completed", None)


@pytest.mark.parametrize("mergeable_state", ["dirty", "behind"])
async def test_a_branch_that_conflicts_with_or_trails_its_base_goes_to_the_agent(client, run, github, mergeable_state):
    github.mergeable_state = mergeable_state

    advanced = await advance(client, run)

    assert (advanced["state"], advanced["pause_reason"], github.merge_requests) == ("dispatching", None, 0)
    assert await attempt_kinds(client, run) == ["implementation", "conflict-fix"]


async def test_a_refused_merge_is_a_conflict_only_when_github_says_so(client, run, github):
    # GitHub had not computed mergeability yet, accepted the request, then refused it for a missing review.
    github.mergeable_state = None
    github.state_after_refusal = "blocked"
    github.merge_response = httpx.Response(405, json={"message": "At least 1 approving review is required"})

    advanced = await advance(client, run)

    assert advanced["state"] == "awaiting_ci" and "repository rule" in advanced["pause_reason"]
    assert github.merge_requests == 1
    assert await attempt_kinds(client, run) == ["implementation"]

    github.state_after_refusal = "dirty"
    github.mergeable_state = None
    conflicted = await advance(client, run)
    assert conflicted["state"] == "dispatching"
    assert await attempt_kinds(client, run) == ["implementation", "conflict-fix"]


@pytest.mark.parametrize(
    ("status", "headers", "kind", "retry_after"),
    [
        (401, {}, "auth", None),
        (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1000600"}, "rate_limited", 600),
        (403, {"retry-after": "5"}, "rate_limited", 60),
        (429, {}, "rate_limited", 60),
        (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "9999999"}, "rate_limited", 3600),
        (403, {"x-ratelimit-remaining": "41"}, "upstream", None),
        (500, {}, "upstream", None),
    ],
)
def test_github_failures_are_classified_from_status_and_headers(status, headers, kind, retry_after):
    error = github_http_error("observation", httpx.Response(status, headers=headers), now=1_000_000)

    assert (error.kind, error.retry_after, error.status_code) == (kind, retry_after, status)
    assert str(error) == f"GitHub observation returned HTTP {status}"


async def test_a_rate_limited_read_carries_its_delay():
    transport = httpx.MockTransport(lambda request: httpx.Response(403, headers={"retry-after": "90"}))
    async with httpx.AsyncClient(base_url="https://api.github.com", transport=transport) as client:
        with pytest.raises(GitHubObservationError) as raised:
            await GitHubActionsReader(client).list_issue_comments("owner/app", 7)
    assert (raised.value.kind, raised.value.retry_after) == ("rate_limited", 90)


async def test_the_attempt_list_sums_up_what_the_run_has_cost(client, run, github):
    github.mergeable_state = "dirty"
    await advance(client, run)

    attempts = (await client.get(f"/api/v1/pipeline-runs/{run['id']}/attempts")).json()

    summary = attempts["summary"]
    assert summary["attempts_by_kind"] == {"implementation": 1, "conflict-fix": 1}
    # The pull request was implemented outside the pipeline and the fix is only planned: nothing was posted yet.
    assert (summary["requests_sent"], summary["quota_limit_replies"]) == (0, 0)
    assert summary["finished_at"] is None and summary["elapsed_seconds"] >= 0


async def test_observation_and_merge_release_transactions_before_io(client, run, github, verify_observation_io_scope):
    verify_observation_io_scope()
    advanced = await advance(client, run)
    assert advanced["state"] == "completed"
    assert github.merge_requests == 1


@pytest.mark.parametrize("mutation", ["pause", "cancel", "project", "lease", "attempt"])
async def test_ci_observation_rejects_changes_before_merge(client, run, github, session, monkeypatch, mutation):
    import asyncio
    from datetime import timedelta
    from uuid import UUID

    from app.features.project_management.pipeline_runs.models import PipelineRun
    from app_testing_base import utc_now
    from sqlalchemy import update

    original = services.PipelineObservationService.observe
    root = f"/api/v1/pipeline-runs/{run['id']}"

    async def observe_then_change(self, config):
        report = await original(self, config)
        # These calls must finish while the observer is still waiting. A retained row lock deadlocks on PostgreSQL.
        if mutation in ("pause", "cancel"):
            response = await asyncio.wait_for(client.post(f"{root}/{mutation}"), 3)
            assert_status_code(response, 200)
        elif mutation == "project":
            project = (await client.get(f"/api/v1/projects/{run['project_id']}")).json()
            response = await asyncio.wait_for(
                client.patch(
                    f"/api/v1/projects/{run['project_id']}",
                    json={
                        "name": "Changed while observing",
                        "enabled": True,
                        "github": project["github"],
                        "expected_revision": project["revision"],
                    },
                ),
                3,
            )
            assert_status_code(response, 200)
        elif mutation == "lease":
            await session.execute(
                update(PipelineRun)
                .where(PipelineRun.id == UUID(run["id"]))
                .values(lease_expires_at=utc_now() - timedelta(seconds=1))
            )
            await session.commit()
            response = await client.post(f"{root}/lease", json={"owner": "other-worker", "ttl_seconds": 60})
            assert_status_code(response, 200)
        else:
            attempts = (await client.get(f"{root}/attempts")).json()["items"]
            response = await asyncio.wait_for(
                client.post(f"{root}/attempts/{attempts[0]['id']}/complete", json={"status": "completed"}), 3
            )
            assert_status_code(response, 200)
        return report

    monkeypatch.setattr(services.PipelineObservationService, "observe", observe_then_change)
    response = await client.post(f"{root}/advance")
    assert_status_code(response, 409)
    assert github.merge_requests == 0
    current = (await client.get(root)).json()
    assert current["state"] == {"pause": "paused", "cancel": "canceled"}.get(mutation, "awaiting_ci")
    if mutation == "lease":
        assert current["lease_owner"] == "other-worker"


async def test_cancel_after_final_ci_read_prevents_merge(client, run, github, monkeypatch):
    original = GitHubActionsReader.observe_pull
    reads = 0
    root = f"/api/v1/pipeline-runs/{run['id']}"

    async def observe_then_cancel(self, *args, **kwargs):
        nonlocal reads
        result = await original(self, *args, **kwargs)
        reads += 1
        if reads == 2:
            assert_status_code(await client.post(f"{root}/cancel"), 200)
        return result

    monkeypatch.setattr(GitHubActionsReader, "observe_pull", observe_then_cancel)
    assert_status_code(await client.post(f"{root}/advance"), 409)
    assert reads == 2
    assert github.merge_requests == 0


async def test_merge_result_cannot_overwrite_a_concurrent_cancel(client, run, github, monkeypatch):
    original = GitHubActionsReader.merge_pull_request
    root = f"/api/v1/pipeline-runs/{run['id']}"

    async def merge_then_cancel(self, *args, **kwargs):
        result = await original(self, *args, **kwargs)
        assert_status_code(await client.post(f"{root}/cancel"), 200)
        return result

    monkeypatch.setattr(GitHubActionsReader, "merge_pull_request", merge_then_cancel)
    assert_status_code(await client.post(f"{root}/advance"), 409)
    assert github.merge_requests == 1
    assert (await client.get(root)).json()["state"] == "canceled"
