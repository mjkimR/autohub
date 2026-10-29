import base64
import json
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import activities, policy, services
from app.features.project_management.sdd.schemas import StartActivityRequest

pytestmark = pytest.mark.unit
BASE = "a" * 40
DRAFT = "---\nid: PROP-demo\nstatus: draft\ntask_kind: feature\n---\n# Demo\n"


class FakeGitHub:
    def __init__(self, proposal=DRAFT, records=("01-gate-plan-intent.yaml",)):
        self.refs = {"main": BASE}
        self.proposal, self.records, self.pulls, self.created = proposal, list(records), [], []
        self.approach, self.unmet, self.errors, self.checkouts = "sdd", [], [], []

    def respond(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/repos/owner/app")
        if path.startswith("/git/ref/heads/"):
            ref = path.removeprefix("/git/ref/heads/")
            return (
                httpx.Response(200, json={"object": {"sha": self.refs[ref]}})
                if ref in self.refs
                else httpx.Response(404)
            )
        if path == "/contents/docs/proposals/PROP-demo/proposal.md":
            if self.proposal is None:
                return httpx.Response(404)
            content = base64.b64encode(self.proposal.encode()).decode()
            return httpx.Response(200, json={"encoding": "base64", "content": content})
        if path == "/contents/docs/proposals/PROP-demo/decisions":
            return httpx.Response(200, json=[{"name": name} for name in self.records])
        if path == "/pulls" and request.method == "GET":
            return httpx.Response(200, json=self.pulls)
        if path == "/pulls" and request.method == "POST":
            body = json.loads(request.content)
            self.created.append(body)
            return httpx.Response(201, json={"number": 42, **body})
        raise AssertionError(f"Unexpected {request.method} {path}")


@pytest.fixture
def started(monkeypatch):
    github, branches, enrolled = FakeGitHub(), [], []
    monkeypatch.setattr(
        activities.pipeline_services,
        "create_github_client",
        lambda token: httpx.AsyncClient(
            base_url="https://api.github.com", transport=httpx.MockTransport(github.respond)
        ),
    )

    async def start_branch(repository, base_sha, branch, token, message, write):
        branches.append((branch, base_sha, message, write))
        github.refs[branch] = "b" * 40
        return "b" * 40

    monkeypatch.setattr(activities, "start_branch", start_branch)

    @asynccontextmanager
    async def checkout(repository, head, base, token):
        github.checkouts.append(base)
        yield Path("/nonexistent")

    async def restore(root):
        return []

    async def cli(root, *args):
        if args == ("spec", "policy"):
            return {"approvals": {}, "development": {"approach": github.approach, "source": "default"}}
        assert args[:2] == ("workflow", "next")
        done = ["intent-proposal"] if github.records else []
        return {"done": done, "unmet": github.unmet, "errors": github.errors}

    monkeypatch.setattr(policy, "checkout", checkout)
    monkeypatch.setattr(policy, "restore", restore)
    monkeypatch.setattr(services, "cli", cli)

    class Runs:
        async def enroll(self, project_id, request):
            enrolled.append(request)
            return SimpleNamespace(id="run")

    class Observer:
        async def get_token(self, connector, provider):
            return "token"

    project = SimpleNamespace(id=uuid4(), github_repository="owner/app", github_connector_id=uuid4())
    starter = activities.ActivityStarter(Observer(), Runs())
    return github, branches, enrolled, project, starter


def request(**overrides):
    return StartActivityRequest(request_id=uuid4(), **overrides)


async def test_planning_starts_plan_branch_with_reviewing_and_a_ready_pull_request(started):
    github, branches, enrolled, project, starter = started
    await starter.start(project, "plan", "demo", request(activity_effort="high"), "user:mj")
    branch, base, message, write = branches[0]
    assert (branch, base, message[0]) == ("plan-demo", BASE, "Start Planning of PROP-demo")
    assert write is not None  # sets status reviewing in the start commit
    assert github.created[0]["head"] == "plan-demo" and github.created[0]["draft"] is False
    assert activities.marker("plan", "demo") in github.created[0]["body"]
    assert enrolled[0].spec_dir == "docs/proposals/PROP-demo" and not enrolled[0].handoff
    assert enrolled[0].activity_effort == "high" and enrolled[0].pull_number == 42


async def test_development_starts_dev_branch_with_a_handoff_first_run(started):
    github, branches, enrolled, project, starter = started
    github.proposal = DRAFT.replace("status: draft", "status: accepted")
    await starter.start(project, "dev", "demo", request(), "user:mj")
    assert branches[0][0] == "dev-demo" and branches[0][3] is None
    assert github.created[0]["draft"] is True and enrolled[0].handoff is True


@pytest.mark.parametrize(
    "activity,existing,override,expected",
    [
        ("plan", False, None, "high"),
        ("dev", False, None, "low"),
        ("plan", True, None, "high"),
        ("dev", False, "medium", "medium"),
    ],
)
async def test_activity_effort_uses_the_proposal_hint_unless_overridden(
    started, activity, existing, override, expected
):
    github, _, enrolled, project, starter = started
    github.proposal = DRAFT.replace("task_kind:", "planning_effort: high\ndev_effort: low\ntask_kind:")
    if activity == "dev":
        github.proposal = github.proposal.replace("status: draft", "status: accepted")
    if existing:
        github.refs["plan-demo"] = "c" * 40
        github.pulls = [{"number": 9, "head": {"ref": "plan-demo"}, "body": activities.marker("plan", "demo")}]
    await starter.start(project, activity, "demo", request(activity_effort=override), "user:mj")
    assert enrolled[0].activity_effort == expected


@pytest.mark.parametrize(
    ("activity", "proposal", "records", "match"),
    [
        ("plan", DRAFT.replace("draft", "reviewing", 1), ("01-gate-plan-intent.yaml",), "starts from a draft"),
        ("plan", DRAFT, (), "Record plan-intent"),
        (
            "plan",
            DRAFT.replace("task_kind", "needs_decompose: true\ntask_kind"),
            ("01-gate-plan-intent.yaml",),
            "decomposition",
        ),
        ("plan", DRAFT.replace("task_kind", "size: XL\ntask_kind"), ("01-gate-plan-intent.yaml",), "size XL"),
        ("plan", None, (), "is not on main"),
        ("dev", DRAFT, (), "accepted proposal"),
        ("dev", DRAFT.replace("draft", "rejected", 1), (), "accepted proposal"),
    ],
)
async def test_start_refuses_a_proposal_in_the_wrong_state(started, activity, proposal, records, match):
    github, branches, _, project, starter = started
    github.proposal, github.records = proposal, list(records)
    with pytest.raises(ProjectError, match=match):
        await starter.start(project, activity, "demo", request(), "user:mj")
    assert not branches and not github.created


async def test_existing_branch_refuses_unless_it_carries_hubs_own_pull_request(started):
    github, branches, enrolled, project, starter = started
    github.refs["plan-demo"] = "c" * 40
    with pytest.raises(ProjectError, match="already exists"):
        await starter.start(project, "plan", "demo", request(), "user:mj")
    github.pulls = [{"number": 9, "head": {"ref": "plan-demo"}, "body": activities.marker("plan", "demo")}]
    await starter.start(project, "plan", "demo", request(), "user:mj")
    assert not branches and not github.created and enrolled[0].pull_number == 9


async def test_slug_must_make_an_activity_branch(started):
    *_, project, starter = started
    with pytest.raises(ProjectError, match="activity branch"):
        await starter.start(project, "plan", "Demo", request(), "user:mj")


@pytest.mark.parametrize("size", ["S", "M", "L", "''"])
async def test_planning_starts_for_every_size_the_gate_allows(started, size):
    github, branches, _, project, starter = started
    github.proposal = DRAFT.replace("task_kind", f"size: {size}\ntask_kind")
    await starter.start(project, "plan", "demo", request(), "user:mj")
    assert branches[0][0] == "plan-demo"


async def test_xl_draft_is_refused_before_any_checkout_or_branch(started):
    github, branches, _, project, starter = started
    github.proposal = DRAFT.replace("task_kind", "size: XL  # decompose\ntask_kind")
    with pytest.raises(ProjectError, match="decompose it in Backlog") as refused:
        await starter.start(project, "plan", "demo", request(), "user:mj")
    assert refused.value.status == 409 and "plan-intent" not in refused.value.detail
    assert not github.checkouts and not branches and not github.created


@pytest.mark.parametrize(
    ("unmet", "errors", "match"),
    [
        (
            [{"name": "frontmatter(proposal.md size S|M|L|)", "satisfied": False, "detail": "size=XL"}],
            [],
            r"size gate \(size=XL\)",
        ),
        (
            [],
            [{"code": "ENVELOPE_INVALID", "message": "secret"}],
            r"invalid workflow evidence on the base \(ENVELOPE_INVALID\)",
        ),
        ([], [], "Record plan-intent"),
    ],
)
async def test_planning_refusal_reports_what_the_base_evaluation_found(started, unmet, errors, match):
    github, branches, _, project, starter = started
    github.records, github.unmet, github.errors = [], unmet, errors
    with pytest.raises(ProjectError, match=match) as refused:
        await starter.start(project, "plan", "demo", request(), "user:mj")
    assert refused.value.status == 409 and "secret" not in refused.value.detail
    assert not branches and not github.created


@pytest.mark.parametrize("activity", ["plan", "dev"])
async def test_incubation_base_refuses_starts_before_creating_branches(started, activity):
    github, branches, enrolled, project, starter = started
    github.approach = "incubation"
    if activity == "dev":
        github.proposal = DRAFT.replace("status: draft", "status: accepted")
    with pytest.raises(ProjectError, match="incubation") as refused:
        await starter.start(project, activity, "demo", request(), "user:mj")
    assert refused.value.status == 409 and refused.value.code == "SDD_LIFECYCLE_INACTIVE"
    assert github.checkouts == [BASE] and not branches and not github.created and not enrolled
