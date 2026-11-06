from uuid import UUID, uuid4

import pytest
from app.features.project_management.pipeline_runs.models import PipelineRun, RunResumeReceipt

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios
from tests.integration.features.project_management.pipeline_runs.test_interactions import answer, ask, state

project = scenarios.project
github = scenarios.github
enroll = scenarios.enroll
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_exact_outcomes_namespace_unknown_and_no_external_reads(client, project, github):
    run = (await enroll(client, project)).json()
    root = f"/api/v1/pipeline-runs/{run['id']}"
    question = (await ask(client, root)).json()
    saved, _ = await answer(client, root, question)
    github.paths.clear()
    for operation, identity, field in [
        ("question", question["id"], "question_id"),
        ("answer", saved["id"], "answer_id"),
    ]:
        result = await client.get(root + "/decision-outcomes/" + identity, params={"operation": operation})
        assert result.status_code == 200, result.text
        assert result.json()["record_state"] == "recorded"
        assert result.json()[field] == identity
        assert "request_digest" not in result.text
    absent = await client.get(root + "/decision-outcomes/" + saved["id"], params={"operation": "resume"})
    assert absent.json()["record_state"] == "unknown"
    assert (await client.get(root + "/decision-outcomes/" + saved["id"])).status_code == 422
    assert (
        await client.get(root + "/decision-outcomes/" + saved["id"], params={"operation": "bad"})
    ).status_code == 422
    assert (await client.get(root + "/decision-outcomes/nope", params={"operation": "answer"})).status_code == 422
    missing = await client.get(
        f"/api/v1/pipeline-runs/{uuid4()}/decision-outcomes/{saved['id']}", params={"operation": "answer"}
    )
    assert missing.status_code == 404
    assert not github.paths


async def test_application_outcome_survives_later_pause_and_receipt_replay(client, project, github):
    run = (await enroll(client, project)).json()
    root = f"/api/v1/pipeline-runs/{run['id']}"
    question = (await ask(client, root)).json()
    saved, _ = await answer(client, root, question)
    request = {
        "request_id": str(uuid4()),
        "expected_revision": (await state(client, root))["revision"],
        "answer_id": saved["id"],
    }
    assert (await client.post(root + "/resume", json=request)).status_code == 200
    await client.post(root + "/pause", json={"reason": "Later stop"})
    github.paths.clear()
    result = (
        await client.get(root + "/decision-outcomes/" + request["request_id"], params={"operation": "resume"})
    ).json()
    assert result["record_state"] == "recorded"
    assert result["applied_attempt_id"]
    assert result["delivery_state"] == "pending"
    assert result["run_state"] == "paused"
    assert not github.paths
    assert (await client.post(root + "/resume", json=request)).status_code == 200
    assert (await state(client, root))["state"] == "paused"
    assert (await client.get(root + "/attempts")).json()["total_count"] == 1


async def test_exact_native_answer_requires_matching_envelope_and_current_context(client, project, github, session):
    run = (await enroll(client, project)).json()
    row = await session.get(PipelineRun, UUID(run["id"]))
    identity = uuid4()
    record = {
        "kind": "answer-envelope",
        "id": str(identity),
        "answers_to": "worker-01.yaml",
        "question": "direction",
        "operation": {"request": "question:worker-01.direction"},
    }
    receipt = RunResumeReceipt(
        id=identity,
        pipeline_run_id=row.id,
        request_digest="hidden",
        decision_evidence={
            "workflow_answer": {"request": "question:worker-01.direction"},
            "decision_records": [record],
        },
    )
    session.add(receipt)
    resolution = {
        "file": "answer-01.yaml",
        "answers_to": "worker-01.yaml",
        "question": "wrong",
        "workflow": "sdd-spec-feature",
        "segment": 0,
    }
    row.sdd_progress = {
        "head_sha": "c" * 40,
        "current": {"workflow": "sdd-spec-feature", "segment": 0},
        "answer_resolutions": [resolution],
    }
    await session.commit()
    url = f"/api/v1/pipeline-runs/{row.id}/decision-outcomes/{identity}"
    assert (await client.get(url, params={"operation": "resume"})).json()["publication_state"] == "pending"
    row.sdd_progress = {**row.sdd_progress, "answer_resolutions": [{**resolution, "question": "direction"}]}
    await session.commit()
    result = (await client.get(url, params={"operation": "resume"})).json()
    assert result["publication_state"] == "published"
    assert result["resolved_envelope"] == "answer-01.yaml"
    row.sdd_progress = {**row.sdd_progress, "current": {"workflow": "sdd-proposal", "segment": 1}}
    await session.commit()
    assert (await client.get(url, params={"operation": "resume"})).json()["publication_state"] == "pending"
