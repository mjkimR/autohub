"""Native policy/approval and PR ownership through the real HTTP/DB boundary."""

from uuid import uuid4

import pytest
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.sdd import services as native
from tests.integration.features.project_management.pipeline_runs import test_merge_stage as merge
from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
github = merge.github
project = scenarios.project
SPEC = "specs/2026-10/20261010-native"
WARNING = {"code": "RECEIPT_STALE", "detail": "Receipt differs from the reviewed runtime"}


def evidence(head=merge.HEAD, base=merge.BASE, approved=False):
    stage = {
        "id": "merge" if approved else "approval",
        "name": "Merge" if approved else "Integration approval",
        "human_gate": None if approved else "dev-integration",
        "exit": ["merged"] if approved else [],
        "skills": [],
    }
    snapshot = {
        "mode": "sdd",
        "provider": "devkit-spec",
        "contract_version": 1,
        "spec_dir": SPEC,
        "cli_version": "fixture",
        "workflow_hash": "hash",
        "workflow_id": "WF-fixture",
        "policy": {"approvals": {"dev-integration": {"policy": "ask"}}},
    }
    return {
        "snapshot": snapshot,
        "head_sha": head,
        "base_sha": base,
        "workflow": {"id": "WF-fixture", "stages": [stage]},
        "current": {"bound": True, "stage": stage, "done": ["review", "reconcile", "report"]},
        "evidence_digest": request_digest({"head": head, "base": base, "approved": approved}),
        "integrated": approved,
    }


@pytest.fixture
def inspector(monkeypatch):
    calls = []

    async def inspect(self, repository, spec_dir, pull, token, **kwargs):
        calls.append(kwargs)
        value = evidence(pull["head"]["sha"], pull["base"]["sha"], kwargs.get("approved", False))
        value["warnings"] = [dict(WARNING)]  # best-effort findings travel with the evidence, never block it
        return value

    monkeypatch.setattr(native.SddService, "inspect", inspect)
    # Native runs keep receiving agent replies even after a push. No external comments in this fixture.
    from app.features.project_management.pipeline_runs.adapters.codex_github_mention import CodexGithubMentionAdapter

    async def replies(*args, **kwargs):
        return []

    monkeypatch.setattr(CodexGithubMentionAdapter, "collect_replies", replies)
    return calls


@pytest.fixture
def unit_branch(github, monkeypatch):
    """The fixture pull request's head is the spec's activity branch, as enrollment requires."""
    original = github.pull
    monkeypatch.setattr(github, "pull", lambda: {**original(), "head": {**original()["head"], "ref": "dev-native"}})


@pytest.fixture
async def run(client, project, github, inspector, unit_branch):
    github.draft = True
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    assert changed.status_code == 200, changed.text
    result = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7, "spec_dir": SPEC})
    assert result.status_code == 201, result.text
    return result.json()


async def decide(client, run, decision=None, **kwargs):
    body = {"request_id": str(uuid4()), "expected_revision": run["revision"], **kwargs}
    if decision:
        body["decision"] = decision
    response = await client.post(f"/api/v1/pipeline-runs/{run['id']}/resume", json=body)
    return response, body


async def test_single_owner_approval_to_ci_merge_and_idempotent_receipt(client, run, github):
    assert run["state"] == "implementing"
    waiting = await merge.advance(client, run)
    assert waiting["state"] == "paused"
    assert github.merge_requests == 0
    approved, body = await decide(client, waiting, "approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["sdd_progress"]["approval"]["actor"].startswith("user:")
    replay = await client.post(f"/api/v1/pipeline-runs/{run['id']}/resume", json=body)
    assert replay.status_code == 200
    assert replay.json()["revision"] == approved.json()["revision"]
    github.draft = False
    integrated = await merge.advance(client, run)
    assert integrated["state"] == "awaiting_ci"
    done = await merge.advance(client, run)
    assert done["state"] == "completed"
    assert github.merge_requests == 1
    replay = await client.post(f"/api/v1/pipeline-runs/{run['id']}/resume", json=body)
    assert replay.status_code == 200 and replay.json()["state"] == "completed"


async def test_resume_never_means_approval_and_reject_stops(client, run, github):
    waiting = await merge.advance(client, run)
    resumed, _ = await decide(client, waiting)
    assert resumed.status_code == 200
    waiting = await merge.advance(client, run)
    assert waiting["state"] == "paused"
    assert not waiting["sdd_progress"].get("approval")
    rejected, _ = await decide(client, waiting, "reject")
    assert rejected.status_code == 200 and rejected.json()["state"] == "canceled"
    assert github.merge_requests == 0


async def test_stale_revision_and_changed_evidence_cannot_approve(client, run, github, monkeypatch):
    waiting = await merge.advance(client, run)
    stale, _ = await decide(client, run, "approve")
    assert stale.status_code == 409
    original = github.pull
    monkeypatch.setattr(github, "pull", lambda: {**original(), "base": {"ref": "main", "sha": "f" * 40}})
    changed, _ = await decide(client, waiting, "approve")
    assert changed.status_code == 409
    assert github.merge_requests == 0


async def test_mode_change_preserves_active_contract(client, run, project):
    current = (await client.get(f"/api/v1/projects/{project['id']}")).json()
    result = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": current["revision"], "project_type": "general"}
    )
    assert result.status_code == 200, result.text
    waiting = await merge.advance(client, run)
    assert waiting["state"] == "paused"
    assert waiting["sdd_snapshot"]["mode"] == "sdd"


async def test_draft_reentry_revokes_approval_and_prevents_merge(client, run, github):
    waiting = await merge.advance(client, run)
    github.draft = False
    approved, _ = await decide(client, waiting, "approve")
    assert approved.status_code == 200
    github.draft = True
    revoked = await merge.advance(client, run)
    assert revoked["state"] == "blocked"
    assert not revoked["sdd_progress"].get("approval")
    assert github.merge_requests == 0


async def test_rework_is_a_new_attempt_without_approval(client, run, github):
    waiting = await merge.advance(client, run)
    changed, _ = await decide(client, waiting, "revise", feedback="Retain the existing API response")
    assert changed.status_code == 200, changed.text
    state = changed.json()
    assert state["state"] == "dispatching"
    assert not state["sdd_progress"].get("approval")
    attempts = (await client.get(f"/api/v1/pipeline-runs/{run['id']}/attempts")).json()["items"]
    assert "Retain the existing API response" in attempts[-1]["request_snapshot"]["instructions"]
    instructions = attempts[-1]["request_snapshot"]["instructions"]
    # Agents hear about the stale receipt but are not told to replace it: that would end this run's contract.
    assert "Hub warning (RECEIPT_STALE): Hub evaluates this pull request" in instructions
    assert "Do not change .devkit/ in this run" in instructions
    assert "Receipt differs" not in instructions
    assert github.merge_requests == 0


async def test_enrollment_attaches_only_the_units_activity_branch(client, project, inspector):
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    assert changed.status_code == 200
    # The fixture pull request is on feature/7; the spec's branch is dev-native.
    refused = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7, "spec_dir": SPEC})
    assert refused.status_code == 422, refused.text
    assert "dev-native" in refused.text and "feature/7" in refused.text
    ready = await client.post(
        f"/api/v1/projects/{project['id']}/sdd/readiness", json={"pull_number": 7, "spec_dir": SPEC}
    )
    assert ready.status_code == 200 and not ready.json()["ready"]
    assert "dev-native" in ready.json()["reason"]
    runs = (await client.get("/api/v1/pipeline-runs", params={"project_id": project["id"]})).json()
    assert runs["total_count"] == 0


async def test_native_enrollment_requires_spec_and_readiness_is_read_only(client, project, inspector, unit_branch):
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    assert changed.status_code == 200
    missing = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7})
    assert missing.status_code == 422
    runtime = await client.get(f"/api/v1/projects/{project['id']}/sdd/runtime")
    assert runtime.status_code == 200, runtime.text
    status = runtime.json()  # ok on a provisioned host; otherwise the detail names the installer
    assert status["ok"] or "install-sdd" in status["detail"]
    ready = await client.post(
        f"/api/v1/projects/{project['id']}/sdd/readiness", json={"pull_number": 7, "spec_dir": SPEC}
    )
    assert ready.status_code == 200 and ready.json()["ready"]
    assert ready.json()["warnings"] == [WARNING]
    runs = (await client.get("/api/v1/pipeline-runs", params={"project_id": project["id"]})).json()
    assert runs["total_count"] == 0


async def test_unexpected_head_after_approval_is_not_merged(client, run, github, monkeypatch):
    waiting = await merge.advance(client, run)
    approved, _ = await decide(client, waiting, "approve")
    assert approved.status_code == 200
    original = github.pull
    monkeypatch.setattr(github, "pull", lambda: {**original(), "head": {"ref": "feature/7", "sha": "f" * 40}})
    revoked = await merge.advance(client, run)
    assert revoked["state"] == "blocked"
    assert not revoked["sdd_progress"].get("approval")
    assert github.merge_requests == 0


async def test_stage_dispatch_and_post_push_question_are_not_skipped(
    client, project, github, inspector, unit_branch, monkeypatch
):
    import json

    from app.features.project_management.pipeline_runs.adapters.base import AgentReply, DeliveryReceipt
    from app.features.project_management.pipeline_runs.adapters.codex_github_mention import CodexGithubMentionAdapter
    from app.features.project_management.pipeline_runs.dispatch import CODEX_CONNECTOR_LOGIN
    from app_testing_base import utc_now

    state = {"head": merge.HEAD, "stage": "build"}
    original = github.pull
    monkeypatch.setattr(github, "pull", lambda: {**original(), "head": {**original()["head"], "sha": state["head"]}})

    async def inspect(self, repository, spec_dir, pull, token, **kwargs):
        value = evidence(state["head"])
        value["current"]["stage"] = {
            "id": state["stage"],
            "human_gate": False,
            "exit": ["tasks-all-checked"],
            "skills": ["sr-review"],
        }
        value["warnings"] = [dict(WARNING)]
        return value

    async def deliver(self, observer, target, request, delivery_number, authorize):
        await authorize()
        return DeliveryReceipt("delivery-1", utc_now(), None)

    monkeypatch.setattr(native.SddService, "inspect", inspect)
    monkeypatch.setattr(CodexGithubMentionAdapter, "deliver", deliver)
    patched = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    assert patched.status_code == 200
    created = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7, "spec_dir": SPEC})
    assert created.status_code == 201, created.text
    run = created.json()
    running = await merge.advance(client, run)
    assert running["state"] == "implementing"
    root = f"/api/v1/pipeline-runs/{run['id']}"
    attempt = (await client.get(root + "/attempts")).json()["items"][0]
    assert running["sdd_progress"]["warnings"] == [WARNING]
    state.update(head="f" * 40, stage="review")
    question = {
        "attempt": attempt["request_snapshot"]["correlation_marker"],
        "head": merge.HEAD,
        "question": "Keep the public API?",
    }

    async def replies(*args):
        return [
            AgentReply(
                "reply-1",
                CODEX_CONNECTOR_LOGIN,
                utc_now(),
                "<!-- autohub-question " + json.dumps(question) + " -->",
                False,
            )
        ]

    monkeypatch.setattr(CodexGithubMentionAdapter, "collect_replies", replies)
    blocked = await merge.advance(client, run)
    assert blocked["state"] == "blocked"
    questions = (await client.get(root + "/questions")).json()["items"]
    assert questions[0]["head_sha"] == "f" * 40
    assert questions[0]["question"] == "Keep the public API?"
    assert github.merge_requests == 0


async def test_decision_audit_survives_revocation(client, run):
    waiting = await merge.advance(client, run)
    approved, _ = await decide(client, waiting, "approve")
    assert approved.status_code == 200
    revoked, _ = await decide(client, approved.json(), "revoke", feedback="Recheck the requirement")
    assert revoked.status_code == 200
    history = await client.get(f"/api/v1/pipeline-runs/{run['id']}/sdd-decisions")
    assert history.status_code == 200, history.text
    rows = history.json()
    assert [row["action"] for row in rows] == ["revoke", "approve"]
    assert rows[0]["prior_approval"]["actor"] == rows[1]["actor"]
    assert rows[1]["head_sha"] == merge.HEAD


async def test_base_change_returns_to_integration_without_merging(client, run, github, monkeypatch):
    waiting = await merge.advance(client, run)
    approved, _ = await decide(client, waiting, "approve")
    assert approved.status_code == 200
    integrated = await merge.advance(client, run)
    assert integrated["state"] == "awaiting_ci"
    original = github.pull
    monkeypatch.setattr(github, "pull", lambda: {**original(), "base": {**original()["base"], "sha": "f" * 40}})

    async def needs_integration(self, repository, spec_dir, pull, token, **kwargs):
        value = evidence(base="f" * 40, approved=True)
        value["integrated"] = False
        value["current"]["stage"] = {
            "id": "integrate",
            "name": "Integrate",
            "skills": ["sr-integrate"],
            "exit": ["lint-ci-clean"],
        }
        return value

    monkeypatch.setattr(native.SddService, "inspect", needs_integration)
    changed = await merge.advance(client, run)
    assert changed["state"] == "dispatching"
    assert changed["sdd_progress"]["approval"]["head_sha"] == merge.HEAD
    assert github.merge_requests == 0


async def test_given_integration_gate_is_approved_without_a_decision_record(client, run, inspector, monkeypatch):
    original = native.SddService.inspect

    async def with_request(self, repository, spec_dir, pull, token, **kwargs):
        value = await original(self, repository, spec_dir, pull, token, **kwargs)
        value["current"]["requests"] = [{"id": "gate:dev-integration", "kind": "approve", "answer": "given"}]
        return value

    monkeypatch.setattr(native.SddService, "inspect", with_request)
    waiting = await merge.advance(client, run)
    assert waiting["state"] == "paused"
    assert waiting["pause_reason"].startswith("dev-integration:")
    approved, _ = await decide(client, waiting, "approve")
    assert approved.status_code == 200, approved.text
    # The gate's answer channel is given: Hub passes --given dev-integration and authors no decision record.
    assert all("operation" not in call for call in inspector)
    assert not approved.json()["sdd_progress"].get("decision_records")
    assert approved.json()["sdd_progress"]["approval"]["source"] == "hub"


async def test_stale_receipt_lint_failure_pauses_without_dispatching(client, run, github, monkeypatch):
    waiting = await merge.advance(client, run)
    approved, _ = await decide(client, waiting, "approve")
    assert approved.status_code == 200
    attempts_path = f"/api/v1/pipeline-runs/{run['id']}/attempts"
    before = len((await client.get(attempts_path)).json()["items"])

    async def stale_lint(self, repository, spec_dir, pull, token, **kwargs):
        value = evidence(approved=True)
        value["current"]["stage"] = {"id": "integrate", "name": "Integrate", "skills": [], "exit": ["lint-ci-clean"]}
        value.update(integrated=False, lint_blocked=True, lint_diagnostic="Final lint did not run against the receipt")
        value["warnings"] = [dict(WARNING)]
        return value

    monkeypatch.setattr(native.SddService, "inspect", stale_lint)
    blocked = await merge.advance(client, run)
    assert blocked["state"] == "blocked"
    assert blocked["pause_reason"] == "Final lint did not run against the receipt"
    assert len((await client.get(attempts_path)).json()["items"]) == before
    resumed, _ = await decide(client, blocked)
    assert resumed.status_code == 200, resumed.text
    assert len((await client.get(attempts_path)).json()["items"]) == before  # resume re-inspects, never dispatches
    assert github.merge_requests == 0


async def test_unresolved_worker_problem_blocks_the_run_and_its_approval(client, run, github, monkeypatch):
    problem = {"file": "worker-02.yaml", "cause": "Build broke", "recovery": "Repair the fixture", "attempts": []}

    async def held(self, repository, spec_dir, pull, token, **kwargs):
        value = evidence(pull["head"]["sha"], pull["base"]["sha"], kwargs.get("approved", False))
        value["hold"] = {"blocked": True, "problems": [problem], "pending_questions": [], "malformed_workers": []}
        value["current"]["gate"] = {"name": "dev-integration", "satisfied": False, "held": True}
        return value

    monkeypatch.setattr(native.SddService, "inspect", held)
    blocked = await merge.advance(client, run)
    assert blocked["state"] == "blocked"
    assert blocked["pause_reason"].startswith("Worker problem unresolved: worker-02.yaml: Build broke")
    approved, _ = await decide(client, blocked, "approve")
    assert approved.status_code == 409  # no gate passes while the unit is held
    assert github.merge_requests == 0


async def test_activity_effort_is_recorded_and_passed_to_the_agent(client, project, github, inspector, unit_branch):
    general = await client.post(
        f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7, "activity_effort": "high"}
    )
    assert general.status_code == 422
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    assert changed.status_code == 200
    github.draft = True
    created = await client.post(
        f"/api/v1/projects/{project['id']}/runs",
        json={"pull_number": 7, "spec_dir": SPEC, "activity_effort": "high"},
    )
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["sdd_snapshot"]["activity_effort"] == "high"
    attempts = (await client.get(f"/api/v1/pipeline-runs/{run['id']}/attempts")).json()["items"]
    assert "Activity effort: high." in attempts[0]["request_snapshot"]["instructions"]


async def test_concurrent_duplicate_approval_has_one_receipt(client, run, is_postgres):
    import asyncio

    if not is_postgres:
        pytest.skip("Row-lock contention requires PostgreSQL")
    waiting = await merge.advance(client, run)
    payload = {"request_id": str(uuid4()), "expected_revision": waiting["revision"], "decision": "approve"}
    root = f"/api/v1/pipeline-runs/{run['id']}"
    results = await asyncio.gather(*(client.post(root + "/resume", json=payload) for _ in range(2)))
    assert all(result.status_code == 200 for result in results), [result.text for result in results]
    history = (await client.get(root + "/sdd-decisions")).json()
    assert len(history) == 1


async def test_spec_runs_are_exact_project_scoped_and_do_not_advance(client, run, project, github):
    path = f"/api/v1/projects/{project['id']}/sdd/runs"
    listed = await client.get(path, params={"spec_dir": SPEC})
    assert listed.status_code == 200, listed.text
    assert [row["id"] for row in listed.json()] == [run["id"]]
    assert listed.json()[0]["revision"] == run["revision"]
    assert (await client.get(path, params={"spec_dir": SPEC + "-other"})).json() == []
    assert (await client.get(path, params={"spec_dir": "../outside"})).status_code == 422
    unknown = await client.get(f"/api/v1/projects/{uuid4()}/sdd/runs", params={"spec_dir": SPEC})
    assert unknown.status_code == 404
    assert github.merge_requests == 0
