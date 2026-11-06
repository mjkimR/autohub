from uuid import UUID, uuid4

import pytest
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
    assert entry["subject_id"] == question["id"]
    assert entry["question_state"] == "open"
    assert not github.paths
    selected = await client.get(root + "/questions/" + question["id"])
    assert selected.status_code == 200
    assert selected.json()["id"] == question["id"]
    reviewed = await client.post(URL + "/review", json={"key": entry["key"], "fingerprint": entry["fingerprint"]})
    assert reviewed.status_code == 200
    assert not github.paths
    await answer(client, root, question)
    updated = (await client.get(URL)).json()["items"][0]
    assert updated["question_state"] == "answered"
    assert updated["waiting_since"] == entry["waiting_since"]
    dismissed = await client.post(
        root + f"/questions/{question['id']}/dismiss",
        json={"expected_revision": (await state(client, root))["revision"], "reason": "No longer needed"},
    )
    assert dismissed.status_code == 200
    assert (await client.get(URL)).json()["items"] == []


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
    second = (await client.get(URL, params={"limit": 100, "cursor": first["next_cursor"]})).json()
    assert len(second["items"]) == 5 and not second["has_more"]
    assert not set(r["key"] for r in first["items"]) & set(r["key"] for r in second["items"])
    assert not github.paths
    assert (await client.get(URL, params={"cursor": "broken"})).status_code == 422
    assert (await client.get(URL, params={"cursor": first["next_cursor"], "kind": "run-question"})).status_code == 422
    assert (await client.get(URL, params={"limit": 101})).status_code == 422
    assert (await client.get(URL, params={"project_id": str(uuid4())})).status_code == 404


async def test_native_generation_and_publication_pending(client, project, github, session):
    enrolled = (await enroll(client, project)).json()
    run = await session.get(PipelineRun, UUID(enrolled["id"]))
    request = {
        "id": "question:worker-01.second",
        "kind": "choose",
        "answer": "envelope",
        "title": "Second question",
        "options": [],
    }
    run.state = "blocked"
    run.sdd_snapshot = {"provider": "devkit-spec", "spec_dir": "specs/test", "policy": {}}
    run.sdd_progress = {"head_sha": "c" * 40, "base_sha": "d" * 40, "current": {"requests": [request]}, "workflow": {}}
    await session.commit()
    first = (await client.get(URL)).json()["items"][0]
    assert first["kind"] == "native-worker-question"
    run = await session.get(PipelineRun, run.id)
    run.sdd_progress = {**run.sdd_progress, "unrelated": "refresh"}
    run.revision += 1
    await session.commit()
    same = (await client.get(URL)).json()["items"][0]
    assert same["fingerprint"] == first["fingerprint"]
    assert same["waiting_since"] == first["waiting_since"]
    run.sdd_progress = {**run.sdd_progress, "head_sha": "e" * 40}
    await session.commit()
    changed = (await client.get(URL)).json()["items"][0]
    assert changed["fingerprint"] != first["fingerprint"]
    stale = await client.post(URL + "/review", json={"key": first["key"], "fingerprint": first["fingerprint"]})
    assert stale.status_code == 409
    run.state = "implementing"
    run.sdd_progress = {
        **run.sdd_progress,
        "decision_records": [
            {
                "kind": "answer-envelope",
                "answers_to": "worker-01.yaml",
                "question": "second",
                "operation": {"request": request["id"]},
            }
        ],
    }
    await session.commit()
    pending = (await client.get(URL)).json()["items"][0]
    assert pending["actionable"] is False
    run.sdd_progress = {**run.sdd_progress, "current": {"requests": []}}
    await session.commit()
    assert (await client.get(URL)).json()["items"][0]["actionable"] is False
    run.sdd_progress = {
        **run.sdd_progress,
        "answer_resolutions": [{"answers_to": "worker-01.yaml", "question": "second"}],
    }
    await session.commit()
    assert (await client.get(URL)).json()["items"] == []


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


async def test_native_review_persists_replacement_and_cas_discards_race(client, project, github, session, monkeypatch):
    from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
    from app.features.project_management.sdd.services import SddService
    from app_layer_base.core.database.transaction import AsyncTransaction

    enrolled = (await enroll(client, project)).json()
    run_id = UUID(enrolled["id"])
    run = await session.get(PipelineRun, run_id)
    request = {
        "id": "question:worker-01.second",
        "kind": "choose",
        "answer": "envelope",
        "title": "Selected request",
        "options": [],
    }
    progress = {
        "head_sha": "c" * 40,
        "base_sha": "d" * 40,
        "evidence_digest": "old",
        "current": {"requests": [request]},
        "workflow": {},
    }
    run.state = "blocked"
    run.sdd_snapshot = {"provider": "devkit-spec", "spec_dir": "specs/test", "policy": {}}
    run.sdd_progress = progress
    await session.commit()
    entry = (await client.get(URL)).json()["items"][0]
    replacement = {**progress, "head_sha": "e" * 40, "evidence_digest": "new"}

    async def inspect(self, *args, **kwargs):
        return dict(replacement)

    monkeypatch.setattr(SddService, "inspect", inspect)
    reviewed = await client.post(URL + "/review", json={"key": entry["key"], "fingerprint": entry["fingerprint"]})
    assert reviewed.status_code == 409
    fresh = (await client.get(URL)).json()["items"][0]
    assert fresh["fingerprint"] != entry["fingerprint"]
    accepted = await client.post(URL + "/review", json={"key": fresh["key"], "fingerprint": fresh["fingerprint"]})
    assert accepted.status_code == 200, accepted.text
    before = accepted.json()

    async def racing_inspect(self, *args, **kwargs):
        async with AsyncTransaction() as other:
            current = await PipelineRunRepository().get(other, run_id, lock=True)
            assert current is not None
            current.revision += 1
            current.pause_reason = "Concurrent stop"
        return {**replacement, "head_sha": "f" * 40}

    monkeypatch.setattr(SddService, "inspect", racing_inspect)
    raced = await client.post(URL + "/review", json={"key": fresh["key"], "fingerprint": fresh["fingerprint"]})
    assert raced.status_code == 409
    retained = (await client.get(f"/api/v1/pipeline-runs/{run_id}")).json()
    assert retained["pause_reason"] == "Concurrent stop"
    assert retained["sdd_progress"]["head_sha"] == before["sdd_progress"]["head_sha"]


@pytest.mark.parametrize("change", ["head", "draft"])
async def test_review_withholds_stale_native_authority(client, project, github, session, monkeypatch, change):
    from app.features.project_management.sdd.services import SddService

    enrolled = (await enroll(client, project)).json()
    await ask(client, f"/api/v1/pipeline-runs/{enrolled['id']}")
    run = await session.get(PipelineRun, UUID(enrolled["id"]))
    run.sdd_snapshot = {"provider": "devkit-spec", "spec_dir": "specs/test", "policy": {}}
    progress = {
        "head_sha": "c" * 40,
        "base_sha": "d" * 40,
        "current": {"requests": []},
        "workflow": {},
        "approval": {"actor": "user:test", "head_sha": "c" * 40, "saw_ready": True},
    }
    run.sdd_progress = progress
    await session.commit()
    entry = (await client.get(URL)).json()["items"][0]
    if change == "head":
        github.pulls[7]["head"]["sha"] = "e" * 40
    else:
        github.pulls[7]["draft"] = True

    async def inspect(self, *args, **kwargs):
        return {k: v for k, v in {**progress, "head_sha": github.pulls[7]["head"]["sha"]}.items() if k != "approval"}

    monkeypatch.setattr(SddService, "inspect", inspect)
    response = await client.post(URL + "/review", json={"key": entry["key"], "fingerprint": entry["fingerprint"]})
    assert response.status_code == 409
    saved = (await client.get(f"/api/v1/pipeline-runs/{run.id}")).json()["sdd_progress"]
    assert not saved.get("approval")
    assert saved["approval_withheld"] is True
    from types import SimpleNamespace

    from app.features.project_management.sdd.progress import SddProgress

    class Observer:
        async def get_token(self, *args):
            return "test"

    # The shared observation path retains the revocation after the inspection saved a replacement head.
    observed = await SddProgress(None).observe(
        run.sdd_snapshot,
        saved,
        SimpleNamespace(connector_id=run.github_connector_id, repository=run.github_repository),
        github.pulls[7],
        Observer(),
    )
    assert not observed["evidence"].get("approval")
    assert observed["evidence"]["approval_withheld"] is True


async def test_native_hub_question_tracks_inspected_generation(client, project, github, session, monkeypatch):
    from app.features.project_management.sdd.services import SddService

    enrolled = (await enroll(client, project)).json()
    await ask(client, f"/api/v1/pipeline-runs/{enrolled['id']}")
    run = await session.get(PipelineRun, UUID(enrolled["id"]))
    from datetime import UTC, datetime
    from app.features.project_management.pipeline_runs import discovery_projection

    clock = [datetime(2026, 11, 3, tzinfo=UTC)]
    monkeypatch.setattr(discovery_projection, "get_current_utc_time", lambda: clock[0])
    question = (await session.scalars(select(RunQuestion).where(RunQuestion.pipeline_run_id == run.id))).one()
    question.created_at = datetime(2026, 11, 1, tzinfo=UTC)
    run.sdd_snapshot = {"provider": "devkit-spec", "spec_dir": "specs/test", "policy": {}}
    progress = {"head_sha": "c" * 40, "base_sha": "d" * 40, "current": {"requests": []}, "workflow": {}}
    run.sdd_progress = progress
    await session.commit()
    old = (await client.get(URL)).json()["items"][0]

    assert old["waiting_since"].startswith("2026-11-03")
    clock[0] = datetime(2026, 11, 4, tzinfo=UTC)

    async def inspect(self, *args, **kwargs):
        return {**progress, "head_sha": "e" * 40}

    monkeypatch.setattr(SddService, "inspect", inspect)
    assert (
        await client.post(URL + "/review", json={"key": old["key"], "fingerprint": old["fingerprint"]})
    ).status_code == 409
    fresh = (await client.get(URL)).json()["items"][0]
    assert fresh["fingerprint"] != old["fingerprint"]
    assert fresh["waiting_since"].startswith("2026-11-04")
    assert fresh["head_sha"] == "e" * 40
    assert question.head_sha == "c" * 40
    clock[0] = datetime(2026, 11, 5, tzinfo=UTC)
    assert (
        await client.post(URL + "/review", json={"key": fresh["key"], "fingerprint": fresh["fingerprint"]})
    ).status_code == 200

    unchanged = (await client.get(URL)).json()["items"][0]
    assert unchanged["waiting_since"] == fresh["waiting_since"]


async def test_native_observation_age_changes_only_after_inspection(client, project, github, session):
    enrolled = (await enroll(client, project)).json()
    run = await session.get(PipelineRun, UUID(enrolled["id"]))
    run.state = "blocked"
    run.sdd_snapshot = {"provider": "devkit-spec", "spec_dir": "specs/test"}
    progress = {
        "head_sha": "c" * 40,
        "observed_at": "2026-11-01T00:00:00+00:00",
        "current": {"requests": [{"id": "gate:plan-intent", "kind": "approve", "title": "Start"}]},
    }
    run.sdd_progress = progress
    await session.commit()
    first = (await client.get(URL)).json()["items"][0]
    run.pause_reason = "Bookkeeping only"
    run.revision += 1
    await session.commit()
    assert (await client.get(URL)).json()["items"][0]["observed_at"] == first["observed_at"]
    run.sdd_progress = {**progress, "observed_at": "2026-11-02T00:00:00+00:00"}
    await session.commit()
    observed = (await client.get(URL)).json()["items"][0]
    assert observed["observed_at"] != first["observed_at"]
    assert observed["waiting_since"] == first["waiting_since"]
