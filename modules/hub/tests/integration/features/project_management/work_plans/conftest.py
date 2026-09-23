import json

import httpx
import pytest
from app.features.project_management.pipelines import services
from app.features.project_management.work_plans.execution import WorkPlanExecution
from app.features.project_management.work_plans.issue_sync import WorkIssueSync
from app.features.project_management.work_plans.kick import WorkPlanKick

LIVE_KICK = WorkPlanKick.run


async def _tick_only(self, project_id, *, run_id=None):
    return None


class GitHubWorkScenario:
    def __init__(self):
        self.refs = {"main": "a" * 40}
        self.files = set()
        self.pulls = {}
        self.issues = {}
        self.parents = {}
        self.requests = []
        self.fail_issues = False
        self.issue_failure_status = 429
        self.lose_issue_response = False
        self.lose_pull_response = False

    def respond(self, request):
        self.requests.append((request.method, request.url.path))
        method, path = request.method, request.url.path.removeprefix("/repos/owner/app")
        body = json.loads(request.content) if request.content else {}
        if path == "/user":
            return httpx.Response(200, json={"login": "operator", "type": "User"})
        if path.startswith("/issues"):
            if self.fail_issues:
                return httpx.Response(self.issue_failure_status, headers={"retry-after": "60"})
            if path == "/issues":
                if method == "POST":
                    n = len(self.issues) + 1
                    self.issues[n] = {
                        **body,
                        "id": n + 1000,
                        "number": n,
                        "html_url": f"https://github.com/owner/app/issues/{n}",
                    }
                    if self.lose_issue_response:
                        self.lose_issue_response = False
                        raise httpx.ReadTimeout("response lost")
                    return httpx.Response(201, json=self.issues[n])
                return httpx.Response(200, json=list(self.issues.values()))
            parts = path.split("/")
            n = int(parts[2])
            if len(parts) == 4 and parts[3] == "parent":
                return (
                    httpx.Response(200, json={"number": self.parents[n]}) if n in self.parents else httpx.Response(404)
                )
            if len(parts) == 4 and parts[3] == "sub_issues":
                self.parents[body["sub_issue_id"] - 1000] = n
                return httpx.Response(201, json={})
            self.issues[n].update(body)
            return httpx.Response(200, json=self.issues[n])
        if path.startswith("/git/matching-refs/heads/"):
            prefix = path.removeprefix("/git/matching-refs/heads/")
            return httpx.Response(
                200,
                json=[
                    {"ref": f"refs/heads/{name}", "object": {"sha": sha}}
                    for name, sha in self.refs.items()
                    if name.startswith(prefix)
                ],
            )
        if path.startswith("/git/ref/heads/"):
            ref = path.removeprefix("/git/ref/heads/")
            return (
                httpx.Response(200, json={"object": {"sha": self.refs[ref]}})
                if ref in self.refs
                else httpx.Response(404)
            )
        if path == "/git/refs":
            self.refs[body["ref"].removeprefix("refs/heads/")] = body["sha"]
            return httpx.Response(201, json={})
        if path.startswith("/contents/"):
            branch = body.get("branch") or request.url.params.get("ref")
            key = (branch, path)
            if method == "PUT":
                self.files.add(key)
                self.refs[branch] = "b" * 40
                return httpx.Response(201, json={})
            return httpx.Response(200, json={}) if key in self.files else httpx.Response(404)
        if path == "/pulls":
            if method == "GET":
                branch = request.url.params["head"].split(":", 1)[1]
                return httpx.Response(200, json=[p for p in self.pulls.values() if p["head"]["ref"] == branch])
            n = len(self.pulls) + 100
            self.pulls[n] = {
                **body,
                "number": n,
                "state": "open",
                "merged": False,
                "html_url": f"https://github.com/owner/app/pull/{n}",
                "head": {"ref": body["head"], "sha": self.refs[body["head"]], "repo": {"full_name": "owner/app"}},
                "base": {"ref": body["base"], "sha": self.refs[body["base"]], "repo": {"full_name": "owner/app"}},
            }
            if self.lose_pull_response:
                self.lose_pull_response = False
                raise httpx.ReadTimeout("response lost")
            return httpx.Response(201, json=self.pulls[n])
        if path.startswith("/pulls/"):
            return httpx.Response(200, json=self.pulls[int(path.split("/")[2])])
        raise AssertionError(f"Unexpected {method} {path}")

    def merge(self, number):
        self.pulls[number].update(state="closed", merged=True, merge_commit_sha="c" * 40)
        self.refs["main"] = "c" * 40


@pytest.fixture
async def setup_work(client, monkeypatch):
    # These scenarios drive the scheduler tick path; immediate follow-up is enabled by `live_kick`.
    monkeypatch.setattr(WorkPlanKick, "run", _tick_only)
    github = GitHubWorkScenario()
    monkeypatch.setattr(
        services,
        "create_github_client",
        lambda token: httpx.AsyncClient(
            base_url="https://api.github.com",
            transport=httpx.MockTransport(github.respond),
        ),
    )
    connector = await client.post(
        "/api/v1/connectors",
        json={
            "name": "github",
            "provider": "github",
            "credentials": {"token": "test-token"},
        },
    )
    assert connector.status_code == 201, connector.text
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Work",
            "repository": "owner/app",
            "github_connector_id": connector.json()["id"],
            "verification": {"workflow": "ci.yml", "required_jobs": ["test"], "event": "pull_request"},
        },
    )
    assert response.status_code == 201, response.text
    project = response.json()

    async def token(*args):
        return "test-token"

    observer = services.PipelineObservationService(token)
    return project, github, WorkPlanExecution(observer), WorkIssueSync(observer)


@pytest.fixture
def live_kick(setup_work, monkeypatch):
    """Immediate follow-up with agent dispatch recorded instead of performed."""
    from unittest.mock import AsyncMock

    from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase

    monkeypatch.setattr(WorkPlanKick, "run", LIVE_KICK)
    dispatch = AsyncMock()
    monkeypatch.setattr(PipelineRunUseCase, "manual_advance", dispatch)
    return dispatch
