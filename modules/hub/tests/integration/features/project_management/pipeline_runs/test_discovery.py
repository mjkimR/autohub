from uuid import UUID, uuid4

import pytest
from app.features.project_management.pipeline_runs.discovery_repo import DecisionDiscoveryRepository
from app.features.project_management.pipeline_runs.models import DecisionEntry, PipelineRun, RunQuestion
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import select

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios
from tests.integration.features.project_management.pipeline_runs.test_interactions import answer, ask, state

project = scenarios.project
github = scenarios.github
enroll = scenarios.enroll
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
URL = "/api/v1/pipeline-runs/decisions"


async def test_discovery_question_lifecycle_and_exact_owner(client, project, github):
    run = (await enroll(client, project)).json()
    root = f"/api/v1/pipeline-runs/{run['id']}"
    question = (await ask(client, root)).json()
    github.paths.clear()
    page = (await client.get(URL)).json()
    entry = page["items"][0]
    assert entry["kind"] == "run-question"
    assert entry["pull_number"] == 7
    assert entry["pull_url"] == run["pull_url"]
    assert entry["run_state"] == "blocked"
    assert entry["subject_id"] == question["id"]
    assert entry["question_state"] == "open"
    assert page["actionable_total_count"] == 1
    assert not github.paths
    selected = await client.get(root + "/questions/" + question["id"])
    assert selected.status_code == 200
    assert selected.json()["id"] == question["id"]
    reviewed = await client.post(URL + "/review", json={"key": entry["key"], "fingerprint": entry["fingerprint"]})
    assert reviewed.status_code == 200
    assert not github.paths
    await answer(client, root, question)
    answered = (await client.get(URL)).json()
    updated = answered["items"][0]
    assert updated["question_state"] == "answered"
    assert updated["actionable"] is True and answered["actionable_total_count"] == 1
    assert updated["waiting_since"] == entry["waiting_since"]
    dismissed = await client.post(
        root + f"/questions/{question['id']}/dismiss",
        json={"expected_revision": (await state(client, root))["revision"], "reason": "No longer needed"},
    )
    assert dismissed.status_code == 200
    emptied = (await client.get(URL)).json()
    assert emptied["items"] == [] and emptied["actionable_total_count"] == 0


async def test_keyset_bounded_and_cursor_filters(client, project, github, session):
    run = (await enroll(client, project)).json()
    now = get_current_utc_time()
    for i in range(105):
        session.add(
            RunQuestion(
                id=uuid4(),
                pipeline_run_id=UUID(run["id"]),
                head_sha="c" * 40,
                question=f"Question {i}",
                actor="test",
                source="operator",
                state="open",
                created_at=now,
            )
        )
    await session.commit()
    github.paths.clear()
    first = (await client.get(URL, params={"limit": 100})).json()
    assert len(first["items"]) == 100 and first["has_more"]
    assert first["actionable_total_count"] == 105
    second = (await client.get(URL, params={"limit": 100, "cursor": first["next_cursor"]})).json()
    assert len(second["items"]) == 5 and not second["has_more"]
    assert second["actionable_total_count"] == 105
    single = (await client.get(URL, params={"limit": 1})).json()
    assert len(single["items"]) == 1 and single["has_more"] and single["actionable_total_count"] == 105
    following = (await client.get(URL, params={"limit": 1, "cursor": single["next_cursor"]})).json()
    assert following["actionable_total_count"] == 105
    for params, total in (
        ({"project_id": run["project_id"]}, 105),
        ({"kind": "run-question"}, 105),
        ({"question_state": "open"}, 105),
        ({"question_state": "answered"}, 0),
        ({"kind": "native-proposal"}, 0),
    ):
        filtered = (await client.get(URL, params={**params, "limit": 1})).json()
        assert filtered["actionable_total_count"] == total, params
        assert bool(filtered["items"]) is bool(total)
    other = await client.post(
        "/api/v1/projects",
        json={
            "name": "Other",
            "repository": "owner/other",
            "github_connector_id": project["github_connector_id"],
            "verification": scenarios.VERIFICATION,
        },
    )
    assert other.status_code == 201
    elsewhere = (await client.get(URL, params={"project_id": other.json()["id"]})).json()
    assert elsewhere["items"] == [] and elsewhere["actionable_total_count"] == 0
    assert not set(r["key"] for r in first["items"]) & set(r["key"] for r in second["items"])
    assert not github.paths
    assert (await client.get(URL, params={"cursor": "broken"})).status_code == 422
    assert (await client.get(URL, params={"cursor": first["next_cursor"], "kind": "run-question"})).status_code == 422
    assert (await client.get(URL, params={"limit": 101})).status_code == 422
    assert (await client.get(URL, params={"project_id": str(uuid4())})).status_code == 404


async def test_count_shares_the_page_transaction(client, project, github, monkeypatch):
    run = (await enroll(client, project)).json()
    await ask(client, f"/api/v1/pipeline-runs/{run['id']}")
    sessions = []
    page, count = DecisionDiscoveryRepository.page, DecisionDiscoveryRepository.count_actionable

    async def record_page(self, session, *args):
        sessions.append(("page", session))
        return await page(self, session, *args)

    async def record_count(self, session, *args):
        sessions.append(("count", session))
        return await count(self, session, *args)

    monkeypatch.setattr(DecisionDiscoveryRepository, "page", record_page)
    monkeypatch.setattr(DecisionDiscoveryRepository, "count_actionable", record_count)
    github.paths.clear()
    response = await client.get(URL, params={"limit": 1})
    assert response.status_code == 200 and response.json()["actionable_total_count"] == 1
    assert [name for name, _ in sessions] == ["page", "count"]
    assert sessions[0][1] is sessions[1][1]
    assert not github.paths


async def test_projection_rolls_back_with_owner(client, project, github, session):
    enrolled = (await enroll(client, project)).json()
    run = await session.get(PipelineRun, UUID(enrolled["id"]))
    run.state = "blocked"
    session.add(
        RunQuestion(
            id=uuid4(),
            pipeline_run_id=run.id,
            head_sha="c" * 40,
            question="Rolled back",
            actor="test",
            source="operator",
            state="open",
        )
    )
    await session.flush()
    assert list(await session.scalars(select(DecisionEntry)))
    await session.rollback()
    assert (await client.get(URL)).json()["items"] == []


async def test_retired_native_evidence_never_creates_live_decisions(client, project, github, session):
    enrolled = (await enroll(client, project)).json()
    row = await session.get(PipelineRun, UUID(enrolled["id"]))
    row.sdd_snapshot = {"provider": "devkit-spec", "spec_dir": "specs/historical"}
    row.sdd_progress = {"current": {"requests": [{"id": "gate:plan-accept", "kind": "approve"}]}}
    row.state = "blocked"
    session.add(
        RunQuestion(
            pipeline_run_id=row.id,
            head_sha="c" * 40,
            question="Historical question",
            actor="test",
            source="agent",
            state="open",
        )
    )
    await session.commit()
    assert (await client.get(URL)).json()["items"] == []
    assert not (await client.get(f"/api/v1/pipeline-runs/{row.id}")).json()["has_pending_decision"]


async def test_optimistic_activity_uses_ordinary_question_projection(client, project, github, session):
    enrolled = (await enroll(client, project)).json()
    row = await session.get(PipelineRun, UUID(enrolled["id"]))
    row.sdd_snapshot = {
        "provider": "repository-agent",
        "execution_version": 2,
        "spec_dir": "docs/proposals/PROP-example",
    }
    await session.commit()
    root = f"/api/v1/pipeline-runs/{row.id}"
    question = await ask(client, root)
    assert question.status_code == 200, question.text
    [entry] = (await client.get(URL)).json()["items"]
    assert entry["kind"] == "run-question"
    assert entry["actionable"]
