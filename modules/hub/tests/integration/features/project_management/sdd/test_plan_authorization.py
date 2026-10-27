"""Proposal approval honors exact published heads, operator questions and explicit withdrawal."""

import json
from uuid import uuid4

import pytest
from app.features.project_management.pipeline_runs.adapters.base import AgentReply
from app.features.project_management.pipeline_runs.adapters.codex_github_mention import CodexGithubMentionAdapter
from app.features.project_management.pipeline_runs.dispatch import CODEX_CONNECTOR_LOGIN
from app.features.project_management.sdd import plan_publication
from app_testing_base import utc_now

from tests.integration.features.project_management.sdd import test_native as scenarios

project = scenarios.project
github = scenarios.github
proposal_run = scenarios.proposal_run
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.fixture
def automatic(proposal_run, monkeypatch):
    state, enroll = proposal_run
    state["complete"] = False
    inspect = scenarios.native.SddService.inspect

    async def delegated(*args, **kwargs):
        value = await inspect(*args, **kwargs)
        value["snapshot"]["policy"]["approvals"]["plan-accept"] = {"policy": "auto"}
        value["base_policy"] = {"approvals": {"plan-accept": {"policy": "auto"}}}
        value["current"].update(
            complete=state["complete"],
            stage=None if state["complete"] else {"id": "feedback-sweep", "exit": [], "skills": []},
            requests=[],
        )
        return value

    monkeypatch.setattr(scenarios.native.SddService, "inspect", delegated)
    return state, enroll


async def ask(client, run):
    root = f"/api/v1/pipeline-runs/{run['id']}"
    response = await client.post(
        root + "/questions",
        json={
            "request_id": str(uuid4()),
            "expected_revision": run["revision"],
            "question": "Confirm scope before accepting",
        },
    )
    assert response.status_code == 200, response.text
    return root, response.json(), (await client.get(root)).json()


async def test_published_decision_head_waits_for_its_own_ci_before_merging(client, proposal_run, github):
    state, enroll = proposal_run
    run = await enroll()
    waiting = await scenarios.merge.advance(client, run)
    accepted, _ = await scenarios.decide(client, waiting, "accept_plan", head_sha=scenarios.merge.HEAD)
    assert accepted.status_code == 200, accepted.text
    assert github.head_sha == scenarios.COMMIT != scenarios.merge.HEAD
    github.ci_head_sha = scenarios.merge.HEAD
    pending = await scenarios.merge.advance(client, run)
    assert pending["state"] == "awaiting_ci" and pending["sdd_progress"].get("approval"), pending
    assert pending["sdd_progress"]["head_sha"] == scenarios.COMMIT and github.merge_requests == 0
    github.ci_head_sha = None
    done = await scenarios.merge.advance(client, run)
    assert done["state"] == "completed" and github.merge_requests == 1 and len(state["decisions"]) == 1


@pytest.mark.parametrize("observed_first", [False, True])
async def test_a_different_head_is_never_allowed_by_the_decision_receipt(client, proposal_run, github, observed_first):
    _, enroll = proposal_run
    run = await enroll()
    waiting = await scenarios.merge.advance(client, run)
    accepted, _ = await scenarios.decide(client, waiting, "accept_plan", head_sha=scenarios.merge.HEAD)
    assert accepted.status_code == 200, accepted.text
    if observed_first:
        github.has_ci = False
        assert (await scenarios.merge.advance(client, run))["state"] == "awaiting_ci"
    github.head_sha = "f" * 40
    blocked = await scenarios.merge.advance(client, run)
    assert blocked["state"] == "blocked" and not blocked["sdd_progress"].get("approval")
    assert github.merge_requests == 0


@pytest.mark.parametrize("decision", ["accept_plan", "reject_plan"])
@pytest.mark.parametrize("answered", [False, True])
async def test_unapplied_hub_question_blocks_a_proposal_decision(client, proposal_run, github, decision, answered):
    state, enroll = proposal_run
    run = await enroll()
    waiting = await scenarios.merge.advance(client, run)
    root, question, current = await ask(client, waiting)
    if answered:
        answer = await client.post(
            root + f"/questions/{question['id']}/answers",
            json={"request_id": str(uuid4()), "expected_revision": current["revision"], "answer": "Keep the scope"},
        )
        assert answer.status_code == 200, answer.text
        current = (await client.get(root)).json()
    result, _ = await scenarios.decide(client, current, decision, head_sha=scenarios.merge.HEAD, feedback="Reviewed")
    assert result.status_code == 409, result.text
    assert not state["decisions"] and github.merge_requests == 0
    questions = (await client.get(root + "/questions")).json()["items"]
    assert questions[0]["state"] == ("answered" if answered else "open")
    dismissed = await client.post(
        root + f"/questions/{question['id']}/dismiss",
        json={"expected_revision": current["revision"], "reason": "Scope reviewed; proceed with the proposal decision"},
    )
    assert dismissed.status_code == 200, dismissed.text
    current = (await client.get(root)).json()
    allowed, _ = await scenarios.decide(client, current, decision, head_sha=scenarios.merge.HEAD, feedback="Reviewed")
    assert allowed.status_code == 200 and len(state["decisions"]) == 1, allowed.text


async def test_a_question_arriving_during_preparation_fences_the_push(client, proposal_run, monkeypatch):
    state, enroll = proposal_run
    run = await enroll()
    waiting = await scenarios.merge.advance(client, run)
    record = plan_publication.record_plan_decision

    async def ask_before_push(*args, **kwargs):
        await ask(client, waiting)
        return await record(*args, **kwargs)

    monkeypatch.setattr(plan_publication, "record_plan_decision", ask_before_push)
    refused, _ = await scenarios.decide(client, waiting, "accept_plan", head_sha=scenarios.merge.HEAD)
    assert refused.status_code == 409 and not state["decisions"], refused.text


@pytest.mark.parametrize("start_before_revoke", [False, True])
async def test_auto_delegation_stays_withdrawn_until_explicit_reapproval(
    client, automatic, github, start_before_revoke
):
    state, enroll = automatic
    run = await enroll()
    if start_before_revoke and run["state"] == "queued":
        run = await scenarios.merge.advance(client, run)
    if not start_before_revoke:
        assert run["state"] == "queued"
        assert (await client.get(f"/api/v1/pipeline-runs/{run['id']}/attempts")).json()["items"] == []
    revoked, _ = await scenarios.decide(client, run, "revoke", feedback="Require my explicit approval")
    assert revoked.status_code == 200, revoked.text
    state["complete"] = True
    resumed, _ = await scenarios.decide(client, revoked.json())
    assert resumed.status_code == 200, resumed.text
    if not start_before_revoke:
        assert (await client.get(f"/api/v1/pipeline-runs/{run['id']}/attempts")).json()["items"] == []
    waiting = await scenarios.merge.advance(client, run)
    assert waiting["state"] == "paused" and waiting["sdd_progress"]["approval_withheld"], waiting
    assert waiting["sdd_progress"]["waiting_for_plan_approval"] and not state["decisions"]
    resumed_again, _ = await scenarios.decide(client, waiting)
    assert resumed_again.status_code == 200, resumed_again.text
    waiting = await scenarios.merge.advance(client, run)
    assert not waiting["sdd_progress"].get("approval") and not state["decisions"]
    approved, _ = await scenarios.decide(client, waiting, "approve")
    assert approved.status_code == 200, approved.text
    published = await scenarios.merge.advance(client, run)
    assert published["state"] == "awaiting_ci" and len(state["decisions"]) == 1, published
    done = await scenarios.merge.advance(client, run)
    assert done["state"] == "completed" and github.merge_requests == 1
    history = (await client.get(f"/api/v1/pipeline-runs/{run['id']}/sdd-decisions")).json()
    assert any(row["action"] == "approve" and row["actor"].startswith("user:") for row in history)


async def test_newly_observed_agent_question_is_saved_before_automatic_acceptance(client, automatic, monkeypatch):
    state, enroll = automatic
    run = await enroll()
    if run["state"] == "queued":
        run = await scenarios.merge.advance(client, run)
    root = f"/api/v1/pipeline-runs/{run['id']}"
    attempt = (await client.get(root + "/attempts")).json()["items"][0]
    question = {
        "attempt": attempt["request_snapshot"]["correlation_marker"],
        "head": scenarios.merge.HEAD,
        "question": "Can the public API change?",
    }

    async def replies(*args, **kwargs):
        return [
            AgentReply(
                "plan-question",
                CODEX_CONNECTOR_LOGIN,
                utc_now(),
                "<!-- autohub-question " + json.dumps(question) + " -->",
                False,
            )
        ]

    monkeypatch.setattr(CodexGithubMentionAdapter, "collect_replies", replies)
    state["complete"] = True
    blocked = await scenarios.merge.advance(client, run)
    assert blocked["state"] == "blocked" and not state["decisions"], blocked
    questions = (await client.get(root + "/questions")).json()["items"]
    assert questions[0]["question"] == "Can the public API change?" and questions[0]["state"] == "open"
