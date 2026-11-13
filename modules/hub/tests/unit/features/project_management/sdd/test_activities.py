import json
from types import SimpleNamespace
from uuid import uuid4

import httpx2
import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import activities
from app.features.project_management.sdd.schemas import StartActivityRequest

pytestmark = pytest.mark.unit
BASE, START = "a" * 40, "b" * 40


class GitHub:
    def __init__(self):
        self.refs, self.pulls, self.writes = {"main": BASE}, [], []
        self.lose = None
        self.reads = []

    def respond(self, request):
        path = request.url.path.removeprefix("/repos/owner/app")
        if request.method == "GET":
            self.reads.append(path)
            if path.startswith("/git/ref/heads/"):
                ref = path.removeprefix("/git/ref/heads/")
                return (
                    httpx2.Response(200, json={"object": {"sha": self.refs[ref]}})
                    if ref in self.refs
                    else httpx2.Response(404)
                )
            if path == f"/git/commits/{BASE}":
                return httpx2.Response(200, json={"tree": {"sha": "c" * 40}})
            if path == "/pulls":
                return httpx2.Response(200, json=self.pulls)
            if path.startswith("/pulls/"):
                pull = next((p for p in self.pulls if str(p["number"]) == path.rsplit("/", 1)[1]), None)
                return httpx2.Response(200, json=pull) if pull else httpx2.Response(404)
            raise AssertionError(f"Repository setup/content must not be read: {path}")
        data = json.loads(request.content)
        self.writes.append((path, data))
        if path == "/git/commits":
            return httpx2.Response(201, json={"sha": START})
        if path == "/git/refs":
            self.refs[data["ref"].removeprefix("refs/heads/")] = data["sha"]
            result = {"object": {"sha": data["sha"]}}
        elif path == "/pulls":
            result = {
                **data,
                "number": 42,
                "state": "open",
                "head": {"ref": data["head"], "sha": START, "repo": {"full_name": "owner/app"}},
                "base": {"ref": data["base"], "repo": {"full_name": "owner/app"}},
            }
            self.pulls.append(result)
        else:
            raise AssertionError(path)
        if self.lose == path:
            self.lose = None
            raise httpx2.ReadTimeout("response lost", request=request)
        return httpx2.Response(201, json=result)


@pytest.fixture
def setup(monkeypatch):
    github, enrolled, checkpoint = GitHub(), [], {}
    monkeypatch.setattr(
        activities.pipeline_services,
        "create_github_client",
        lambda token: httpx2.AsyncClient(
            base_url="https://api.github.com", transport=httpx2.MockTransport(github.respond)
        ),
    )

    class Runs:
        async def enroll(self, project_id, request, **kwargs):
            enrolled.append(request)
            return SimpleNamespace(id=uuid4())

    class Observer:
        async def get_token(self, connector, provider):
            return "token"

    async def retain(**values):
        checkpoint.update(values)

    return (
        github,
        enrolled,
        checkpoint,
        retain,
        activities.ActivityStarter(Observer(), Runs()),
        SimpleNamespace(id=uuid4(), github_repository="owner/app", github_connector_id=uuid4()),
    )


@pytest.mark.parametrize("activity", ["plan", "dev"])
async def test_start_is_github_only_draft_without_reading_repository_eligibility(setup, activity):
    github, enrolled, checkpoint, retain, starter, project = setup
    request = StartActivityRequest(request_id=uuid4(), activity_effort="high")
    await starter.start(project, activity, "demo", request, "operator", checkpoint=retain, saved=checkpoint)
    assert [p for p, _ in github.writes] == ["/git/commits", "/git/refs", "/pulls"]
    commit = github.writes[0][1]
    assert commit["tree"] == "c" * 40 and commit["parents"] == [BASE]
    assert github.pulls[0]["draft"] is True
    assert enrolled[0].handoff is (activity == "dev")
    assert enrolled[0].activity_effort == "high"
    assert checkpoint["initial_sha"] == START and checkpoint["pull_number"] == 42
    assert not any("contents" in p for p in github.reads)


@pytest.mark.parametrize("lost", ["/git/refs", "/pulls"])
async def test_response_loss_recovers_same_saved_candidate_without_duplicate_writes(setup, lost):
    github, enrolled, checkpoint, retain, starter, project = setup
    github.lose = lost
    request = StartActivityRequest(request_id=uuid4())
    with pytest.raises(Exception, match="not confirmed"):
        await starter.start(project, "plan", "demo", request, "operator", checkpoint=retain, saved=checkpoint)
    assert checkpoint["initial_sha"] == START
    await starter.start(project, "plan", "demo", request, "operator", checkpoint=retain, saved=checkpoint)
    assert [p for p, _ in github.writes].count("/git/refs") == 1
    assert [p for p, _ in github.writes].count("/pulls") == 1
    assert len(github.pulls) == len(enrolled) == 1


async def test_unrelated_branch_is_never_adopted(setup):
    github, _, checkpoint, retain, starter, project = setup
    github.refs["plan-demo"] = "d" * 40
    with pytest.raises(ProjectError, match="different owner") as error:
        await starter.start(
            project,
            "plan",
            "demo",
            StartActivityRequest(request_id=uuid4()),
            "operator",
            checkpoint=retain,
            saved=checkpoint,
        )
    assert error.value.code == "SDD_BRANCH_EXISTS" and github.writes == []


async def test_missing_original_ref_does_not_create_replacement(setup):
    github, _, checkpoint, retain, starter, project = setup
    checkpoint.update(initial_sha=START, branch="plan-demo", base_sha=BASE, ref_attempted=True)
    with pytest.raises(ProjectError, match="uncertain"):
        await starter.start(
            project,
            "plan",
            "demo",
            StartActivityRequest(request_id=uuid4()),
            "operator",
            checkpoint=retain,
            saved=checkpoint,
        )
    assert github.writes == []


async def test_closed_original_pr_is_not_replaced(setup):
    github, _, checkpoint, retain, starter, project = setup
    request = StartActivityRequest(request_id=uuid4())
    await starter.start(project, "plan", "demo", request, "operator", checkpoint=retain, saved=checkpoint)
    github.pulls[0]["state"] = "closed"
    writes = len(github.writes)
    with pytest.raises(ProjectError, match="already closed"):
        await starter.start(project, "plan", "demo", request, "operator", checkpoint=retain, saved=checkpoint)
    assert len(github.writes) == writes
