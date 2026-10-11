"""Native policy/approval and PR ownership through the real HTTP/DB boundary."""

from uuid import uuid4

import pytest
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.specrig import services as native
from tests.integration.features.project_management.pipeline_runs import test_merge_stage as merge
from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
github = merge.github
project = scenarios.project
SPEC = "specs/2026-10/20261010-native"


def evidence(head=merge.HEAD, base=merge.BASE, approved=False):
    stage = {
        "id": "merge" if approved else "approval",
        "name": "Merge" if approved else "G3",
        "human_gate": not approved,
        "exit": ["merged" if approved else "approval-given"],
        "skills": [],
    }
    snapshot = {
        "mode": "specrig",
        "spec_dir": SPEC,
        "cli_version": "fixture",
        "workflow_hash": "hash",
        "workflow_id": "WF-fixture",
        "policy": {"workflow.approvals.integration": "ask"},
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
        return evidence(pull["head"]["sha"], pull["base"]["sha"], kwargs.get("approved", False))

    monkeypatch.setattr(native.SpecrigService, "inspect", inspect)
    # Native runs keep receiving agent replies even after a push. No external comments in this fixture.
    from app.features.project_management.pipeline_runs.adapters.codex_github_mention import CodexGithubMentionAdapter

    async def replies(*args, **kwargs):
        return []

    monkeypatch.setattr(CodexGithubMentionAdapter, "collect_replies", replies)
    return calls


@pytest.fixture
async def run(client, project, github, inspector):
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "specrig"}
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
    assert approved.json()["specrig_progress"]["approval"]["actor"].startswith("user:")
    replay = await client.post(f"/api/v1/pipeline-runs/{run['id']}/resume", json=body)
    assert replay.status_code == 200
    assert replay.json()["revision"] == approved.json()["revision"]
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
    assert not waiting["specrig_progress"].get("approval")
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
    assert waiting["specrig_snapshot"]["mode"] == "specrig"


async def test_draft_reentry_revokes_approval_and_prevents_merge(client, run, github):
    waiting = await merge.advance(client, run)
    approved, _ = await decide(client, waiting, "approve")
    assert approved.status_code == 200
    github.draft = True
    revoked = await merge.advance(client, run)
    assert revoked["state"] == "blocked"
    assert not revoked["specrig_progress"].get("approval")
    assert github.merge_requests == 0


async def test_rework_is_a_new_attempt_without_approval(client, run, github):
    waiting = await merge.advance(client, run)
    changed, _ = await decide(client, waiting, "revise", feedback="Retain the existing API response")
    assert changed.status_code == 200, changed.text
    state = changed.json()
    assert state["state"] == "dispatching"
    assert not state["specrig_progress"].get("approval")
    attempts = (await client.get(f"/api/v1/pipeline-runs/{run['id']}/attempts")).json()["items"]
    assert "Retain the existing API response" in attempts[-1]["request_snapshot"]["instructions"]
    assert github.merge_requests == 0


async def test_native_enrollment_requires_spec_and_readiness_is_read_only(client, project, inspector):
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "specrig"}
    )
    assert changed.status_code == 200
    missing = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7})
    assert missing.status_code == 422
    ready = await client.post(
        f"/api/v1/projects/{project['id']}/specrig/readiness", json={"pull_number": 7, "spec_dir": SPEC}
    )
    assert ready.status_code == 200 and ready.json()["ready"]
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
    assert not revoked["specrig_progress"].get("approval")
    assert github.merge_requests == 0


async def test_stage_dispatch_and_post_push_question_are_not_skipped(client, project, github, inspector, monkeypatch):
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
        return value

    async def deliver(self, observer, target, request, delivery_number, authorize):
        await authorize()
        return DeliveryReceipt("delivery-1", utc_now(), None)

    monkeypatch.setattr(native.SpecrigService, "inspect", inspect)
    monkeypatch.setattr(CodexGithubMentionAdapter, "deliver", deliver)
    patched = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "specrig"}
    )
    assert patched.status_code == 200
    created = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7, "spec_dir": SPEC})
    assert created.status_code == 201, created.text
    run = created.json()
    running = await merge.advance(client, run)
    assert running["state"] == "implementing"
    root = f"/api/v1/pipeline-runs/{run['id']}"
    attempt = (await client.get(root + "/attempts")).json()["items"][0]
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
    history = await client.get(f"/api/v1/pipeline-runs/{run['id']}/specrig-decisions")
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

    monkeypatch.setattr(native.SpecrigService, "inspect", needs_integration)
    changed = await merge.advance(client, run)
    assert changed["state"] == "dispatching"
    assert changed["specrig_progress"]["approval"]["head_sha"] == merge.HEAD
    assert github.merge_requests == 0


async def test_concurrent_duplicate_approval_has_one_receipt(client, run, is_postgres):
    import asyncio

    if not is_postgres:
        pytest.skip("Row-lock contention requires PostgreSQL")
    waiting = await merge.advance(client, run)
    payload = {"request_id": str(uuid4()), "expected_revision": waiting["revision"], "decision": "approve"}
    root = f"/api/v1/pipeline-runs/{run['id']}"
    results = await asyncio.gather(*(client.post(root + "/resume", json=payload) for _ in range(2)))
    assert all(result.status_code == 200 for result in results), [result.text for result in results]
    history = (await client.get(root + "/specrig-decisions")).json()
    assert len(history) == 1
