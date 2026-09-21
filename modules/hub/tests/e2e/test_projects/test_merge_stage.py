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

pytestmark = [pytest.mark.e2e, pytest.mark.real_commit]
HEAD = "c" * 40
BASE = "d" * 40
ROOT = "/repos/owner/app"


class MergeScenario:
    def __init__(self) -> None:
        self.mergeable_state: str | None = "clean"
        # The state GitHub reports once a merge was refused; defaults to the state before it.
        self.state_after_refusal: str | None = None
        self.merge_response = httpx.Response(200, json={"merged": True, "sha": "e" * 40})
        self.merge_requests = 0

    def pull(self) -> dict:
        return {
            "number": 7,
            "state": "open",
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
            "conclusion": "success",
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
            return httpx.Response(200, json={"total_count": 1, "workflow_runs": [workflow_run]})
        if path == "/actions/runs/1/jobs":
            job = {"id": 1, "name": "lint", "status": "completed", "conclusion": "success", "html_url": None}
            return httpx.Response(200, json={"total_count": 1, "jobs": [job]})
        if path == "/actions/runs/1":
            return httpx.Response(200, json=workflow_run)
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
async def run(client, github) -> dict:
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


@pytest.mark.parametrize(("mergeable_state", "said"), [("blocked", "branch protection"), ("draft", "is a draft")])
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

    assert advanced["state"] == "awaiting_ci" and "branch protection" in advanced["pause_reason"]
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
