import base64
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from app.features.project_management.sdd import proposals

pytestmark = pytest.mark.unit


def anchor(status, extra=""):
    return (
        f"---\nid: PROP-x\ntitle: Title {status}\nstatus: {status}  # comment\ntask_kind: feature\n{extra}---\n# Body\n"
    )


def run(state="blocked", unit_status="reviewing", requests=("gate:plan-accept",), hold=None):
    progress = {
        "head_sha": "a" * 40,
        "unit_status": unit_status,
        "current": {"requests": [{"id": r} for r in requests]},
        "hold": hold or {},
    }
    return SimpleNamespace(id=uuid4(), state=state, revision=4, pause_reason="x", pull_number=7, sdd_progress=progress)


def test_actions_follow_the_proposal_lifecycle():
    draft = proposals.proposal_state("a", anchor("draft"), set(), {}, None)
    assert draft["actions"] == ["start_planning"] and draft["display_status"] == "draft"
    planning = proposals.proposal_state("a", anchor("draft"), {"plan-a"}, {"plan-a": 3}, None)
    assert planning["actions"] == [] and planning["display_status"] == "reviewing" and planning["plan_pull"] == 3
    decompose = proposals.proposal_state("a", anchor("draft", "needs_decompose: true\n"), set(), {}, None)
    assert decompose["actions"] == [] and "decomposition" in decompose["note"]
    waiting = proposals.waiting_run([run()])
    assert waiting is not None and waiting["plan_accept_open"] and waiting["head_sha"] == "a" * 40
    reviewing = proposals.proposal_state("a", anchor("draft"), {"plan-a"}, {}, waiting)
    assert reviewing["actions"] == ["accept", "reject"]
    accepted = proposals.proposal_state("a", anchor("accepted"), {"plan-a"}, {}, None)
    assert accepted["actions"] == ["start_development"]
    developing = proposals.proposal_state("a", anchor("accepted"), {"dev-a"}, {}, None)
    assert developing["actions"] == []
    rejected = proposals.proposal_state("a", anchor("rejected"), {"plan-a"}, {}, waiting)
    assert rejected["actions"] == [] and "hygiene" in rejected["note"]


@pytest.mark.parametrize(
    "runs",
    [
        [run(state="implementing")],
        [run(unit_status="accepted")],
        [run(requests=())],
        [run(hold={"blocked": True})],
        [run(hold={"pending_questions": [{"id": "q1"}]})],
    ],
)
def test_decisions_open_only_on_a_waiting_unheld_reviewing_run(runs):
    waiting = proposals.waiting_run(runs)
    assert waiting is not None and not waiting["plan_accept_open"]


def test_finished_runs_are_not_waiting():
    assert proposals.waiting_run([run(state="completed")]) is None


async def test_listing_reads_base_proposals_branches_and_pulls(monkeypatch):
    def content(text):
        return {"encoding": "base64", "content": base64.b64encode(text.encode()).decode()}

    def respond(request):
        path = request.url.path.removeprefix("/repos/owner/app")
        if path == "/git/ref/heads/main":
            return httpx.Response(200, json={"object": {"sha": "b" * 40}})
        if path == "/contents/docs/proposals":
            names = ["PROP-alpha", "PROP-beta", "README.md", "PROP-Bad"]
            return httpx.Response(
                200, json=[{"name": n, "type": "file" if n.endswith(".md") else "dir"} for n in names]
            )
        if path == "/git/matching-refs/heads/plan-":
            return httpx.Response(200, json=[{"ref": "refs/heads/plan-alpha"}])
        if path == "/git/matching-refs/heads/dev-":
            return httpx.Response(200, json=[])
        if path == "/pulls":
            return httpx.Response(200, json=[{"number": 5, "head": {"ref": "plan-alpha"}}])
        if path == "/contents/docs/proposals/PROP-alpha/proposal.md":
            return httpx.Response(200, json=content(anchor("draft")))
        if path == "/contents/docs/proposals/PROP-beta/proposal.md":
            return httpx.Response(200, json=content(anchor("accepted")))
        raise AssertionError(path)

    monkeypatch.setattr(
        proposals.pipeline_services,
        "create_github_client",
        lambda token: httpx.AsyncClient(base_url="https://api.github.com", transport=httpx.MockTransport(respond)),
    )

    class Observer:
        async def get_token(self, *args):
            return "token"

    async def runs_for(unit):
        return []

    project = SimpleNamespace(github_repository="owner/app", github_connector_id=uuid4())
    listed = await proposals.list_proposals(Observer(), project, "main", runs_for)
    assert listed["base_sha"] == "b" * 40 and not listed["truncated"]
    alpha, beta = listed["items"]
    assert (alpha["slug"], alpha["display_status"], alpha["plan_pull"], alpha["actions"]) == (
        "alpha",
        "reviewing",
        5,
        [],
    )
    assert (beta["slug"], beta["status"], beta["actions"]) == ("beta", "accepted", ["start_development"])
