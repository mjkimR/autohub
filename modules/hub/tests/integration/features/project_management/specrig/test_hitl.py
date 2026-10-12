"""Decisions survive stage handoffs, no-op answers, polling and manual overrides."""

from datetime import timedelta
from uuid import UUID

import pytest
from app.features.project_management.pipeline_runs.adapters.base import DeliveryReceipt
from app.features.project_management.pipeline_runs.adapters.codex_github_mention import CodexGithubMentionAdapter
from app.features.project_management.pipeline_runs.models import ExecutionAttempt, PipelineRunState
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.specrig import services as native
from app_layer_base.core.database.transaction import AsyncTransaction
from app_testing_base import utc_now
from tests.integration.features.project_management.pipeline_runs import test_interactions as interaction
from tests.integration.features.project_management.specrig import test_native as scenarios

github = scenarios.github
project = scenarios.project
inspector = scenarios.inspector
run = scenarios.run
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.fixture
def delivery(monkeypatch):
    async def deliver(self, observer, target, request, delivery_number, authorize):
        await authorize()
        return DeliveryReceipt("hitl-delivery", utc_now(), None)

    monkeypatch.setattr(CodexGithubMentionAdapter, "deliver", deliver)


async def answered(client, run):
    root = f"/api/v1/pipeline-runs/{run['id']}"
    question = (await interaction.ask(client, root, "Keep the public API?")).json()
    answer, _ = await interaction.answer(client, root, question, "Yes, keep it unchanged")
    await interaction.answer(client, root, question, "Unselected alternative: replace the API")
    current = await interaction.state(client, root)
    response, _ = await scenarios.decide(client, current, answer_id=answer["id"])
    assert response.status_code == 200, response.text
    return root


async def test_applied_question_and_answer_reach_next_stage(client, run, github, delivery, monkeypatch):
    root = await answered(client, run)
    first = (await client.get(root + "/attempts")).json()["items"][-1]
    assert "Keep the public API?" in first["request_snapshot"]["instructions"]
    await scenarios.merge.advance(client, run)
    original = github.pull
    monkeypatch.setattr(github, "pull", lambda: {**original(), "head": {**original()["head"], "sha": "f" * 40}})

    async def inspect(self, repository, spec_dir, pull, token, **kwargs):
        value = scenarios.evidence(head="f" * 40)
        value["current"]["stage"] = {
            "id": "review",
            "human_gate": False,
            "exit": ["review-passed"],
            "skills": ["sr-review"],
        }
        return value

    monkeypatch.setattr(native.SpecrigService, "inspect", inspect)
    next_state = await scenarios.merge.advance(client, run)
    assert next_state["state"] == "dispatching"
    attempts = (await client.get(root + "/attempts")).json()["items"]
    instructions = attempts[-1]["request_snapshot"]["instructions"]
    assert "Keep the public API?" in instructions
    assert "Yes, keep it unchanged" in instructions
    assert "Unselected alternative" not in instructions
    assert "approval" not in next_state["specrig_progress"]


async def test_no_change_answer_returns_to_gate_without_fabricated_push(client, run, github, delivery):
    await answered(client, run)
    await scenarios.merge.advance(client, run)
    github.draft = False
    current = await scenarios.merge.advance(client, run)
    assert current["state"] == "paused"
    assert not current["specrig_progress"].get("approval")
    assert not current["specrig_progress"].get("rework_head")
    approved, _ = await scenarios.decide(client, current, "approve")
    assert approved.status_code == 200


async def test_rework_times_out_and_generic_resume_preserves_requirement(client, run, delivery):
    waiting = await scenarios.merge.advance(client, run)
    changed, _ = await scenarios.decide(client, waiting, "revise", feedback="Keep the API unchanged")
    assert changed.status_code == 200
    await scenarios.merge.advance(client, run)
    root = f"/api/v1/pipeline-runs/{run['id']}"
    attempt = (await client.get(root + "/attempts")).json()["items"][-1]
    async with AsyncTransaction() as session:
        row = await session.get(ExecutionAttempt, UUID(attempt["id"]))
        assert row is not None
        row.started_at = utc_now() - timedelta(hours=2)
    current = await scenarios.merge.advance(client, run)
    assert current["state"] == "blocked"
    assert "45 minutes" in current["pause_reason"]
    resumed, _ = await scenarios.decide(client, current)
    assert resumed.status_code == 200
    assert resumed.json()["specrig_progress"]["rework_head"] == scenarios.merge.HEAD
    assert not resumed.json()["specrig_progress"].get("approval")
    retried = (await client.get(root + "/attempts")).json()["items"][-1]
    assert retried["id"] != attempt["id"]
    assert "Keep the API unchanged" in retried["request_snapshot"]["instructions"]


async def test_ready_pr_records_g3_approval_and_audit(client, run, github):
    github.draft = False
    current = await scenarios.merge.advance(client, run)
    assert current["state"] == "implementing"
    assert current["specrig_progress"]["approval"]["source"] == "pr-ready"
    records = (await client.get(f"/api/v1/pipeline-runs/{run['id']}/specrig-decisions")).json()
    assert records[0]["actor"] == "github:pr-ready"
    assert records[0]["head_sha"] == scenarios.merge.HEAD
    assert records[0]["base_sha"] == scenarios.merge.BASE


async def test_g3_polling_wakes_ready_but_not_manual_pause(client, run, github):
    waiting = await scenarios.merge.advance(client, run)
    assert waiting["state"] == "paused"
    unchanged = await scenarios.merge.advance(client, run)
    assert unchanged["revision"] == waiting["revision"]
    async with AsyncTransaction() as session:
        selected = await PipelineRunRepository().list_active(
            session,
            UUID(run["project_id"]),
            limit=10,
            ready_at=utc_now() + timedelta(minutes=6),
            states=(PipelineRunState.PAUSED,),
        )
        assert [str(row.id) for row in selected] == [run["id"]]
        assert await PipelineRunRepository().count_started(session, UUID(run["project_id"])) == 0
    github.draft = False
    approved = await scenarios.merge.advance(client, run)
    assert approved["specrig_progress"]["approval"]["source"] == "pr-ready"
    await client.post(f"/api/v1/pipeline-runs/{run['id']}/pause")
    unchanged = await scenarios.merge.advance(client, run)
    assert unchanged["state"] == "paused"
    async with AsyncTransaction() as session:
        assert not await PipelineRunRepository().list_active(
            session,
            UUID(run["project_id"]),
            limit=10,
            ready_at=utc_now() + timedelta(minutes=6),
            states=(PipelineRunState.PAUSED,),
        )


async def test_manual_pause_disables_existing_g3_wait(client, run, github):
    waiting = await scenarios.merge.advance(client, run)
    assert waiting["specrig_progress"]["waiting_for_approval"]
    root = f"/api/v1/pipeline-runs/{run['id']}"
    paused = (await client.post(root + "/pause")).json()
    github.draft = False
    unchanged = await scenarios.merge.advance(client, run)
    assert unchanged["revision"] == paused["revision"]
    assert unchanged["state"] == "paused"
    assert not unchanged["specrig_progress"].get("approval")
    assert not unchanged["specrig_progress"].get("waiting_for_approval")


async def test_revoke_cannot_be_undone_by_ready_or_generic_resume(client, run, github):
    github.draft = False
    approved = await scenarios.merge.advance(client, run)
    revoked, _ = await scenarios.decide(client, approved, "revoke", feedback="Recheck scope")
    assert revoked.status_code == 200
    resumed, _ = await scenarios.decide(client, revoked.json())
    assert resumed.status_code == 200
    waiting = await scenarios.merge.advance(client, run)
    assert waiting["state"] == "paused"
    assert not waiting["specrig_progress"].get("approval")
    assert github.merge_requests == 0
