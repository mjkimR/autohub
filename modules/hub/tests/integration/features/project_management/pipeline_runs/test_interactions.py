import asyncio
import json
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from app.features.project_management.pipeline_runs.models import RunAnswer
from app_testing_base import utc_now

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

github = scenarios.github
project = scenarios.project
mention_github = scenarios.mention_github
enroll = scenarios.enroll


pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def state(client, root):
    return (await client.get(root)).json()


async def ask(client, root, text="Choose the empty-state behavior"):
    return await client.post(
        root + "/questions",
        json={
            "request_id": str(uuid4()),
            "expected_revision": (await state(client, root))["revision"],
            "question": text,
        },
    )


async def answer(client, root, question, text="Show an empty list"):
    payload = {"request_id": str(uuid4()), "expected_revision": (await state(client, root))["revision"], "answer": text}
    response = await client.post(root + f"/questions/{question['id']}/answers", json=payload)
    assert response.status_code == 200, response.text
    return response.json(), payload


async def test_answer_is_saved_without_execution_then_applied_once(client, project, github, session):
    run = (await enroll(client, project)).json()
    root = f"/api/v1/pipeline-runs/{run['id']}"
    asked = await ask(client, root)
    assert asked.status_code == 200, asked.text
    question = asked.json()
    response, answer_payload = await answer(client, root, question)
    assert (await state(client, root))["state"] == "blocked"
    assert (await client.get(root + "/attempts")).json()["total_count"] == 0
    replay_answer = await client.post(root + f"/questions/{question['id']}/answers", json=answer_payload)
    assert replay_answer.status_code == 200, replay_answer.text
    assert replay_answer.json()["id"] == response["id"]
    refreshed_retry = await client.post(
        root + f"/questions/{question['id']}/answers",
        json=answer_payload | {"expected_revision": (await state(client, root))["revision"]},
    )
    assert refreshed_retry.status_code == 200, refreshed_retry.text
    assert refreshed_retry.json()["id"] == response["id"]
    assert len((await client.get(root + "/questions")).json()["items"][0]["answers"]) == 1
    payload = {
        "request_id": str(uuid4()),
        "expected_revision": (await state(client, root))["revision"],
        "answer_id": response["id"],
    }
    resumed = await client.post(root + "/resume", json=payload)
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["state"] == "dispatching"
    replay = await client.post(root + "/resume", json=payload)
    assert replay.status_code == 200
    attempts = (await client.get(root + "/attempts")).json()["items"]
    assert len(attempts) == 1
    assert "Show an empty list" in attempts[0]["request_snapshot"]["instructions"]
    assert "Choose the empty-state behavior" in attempts[0]["request_snapshot"]["instructions"]
    saved = await session.get(RunAnswer, UUID(response["id"]))
    assert str(saved.applied_attempt_id) == attempts[0]["id"]
    assert (await client.get(root + "/questions")).json()["items"][0]["state"] == "applied"
    conflict = await client.post(root + "/resume", json=payload | {"answer_id": None})
    assert conflict.status_code == 409


async def test_pending_question_and_changed_head_require_explicit_resolution(client, project, github):
    run = (await enroll(client, project)).json()
    root = f"/api/v1/pipeline-runs/{run['id']}"
    question = (await ask(client, root)).json()
    revision = (await state(client, root))["revision"]
    blocked = await client.post(root + "/resume", json={"request_id": str(uuid4()), "expected_revision": revision})
    assert blocked.status_code == 409
    response, _ = await answer(client, root, question)
    github.pulls[7]["head"]["sha"] = "f" * 40
    payload = {
        "request_id": str(uuid4()),
        "expected_revision": (await state(client, root))["revision"],
        "answer_id": response["id"],
    }
    assert (await client.post(root + "/resume", json=payload)).status_code == 409
    dismissed = await client.post(
        root + f"/questions/{question['id']}/dismiss",
        json={
            "expected_revision": payload["expected_revision"],
            "reason": "Inspected updated implementation; clarification no longer needed",
        },
    )
    assert dismissed.status_code == 200
    assert (await state(client, root))["state"] == "blocked"


async def test_stale_answers_and_missing_resume_contract_do_not_mutate(client, project, github):
    run = (await enroll(client, project)).json()
    root = f"/api/v1/pipeline-runs/{run['id']}"
    question = (await ask(client, root)).json()
    response = await client.post(
        root + f"/questions/{question['id']}/answers",
        json={"request_id": str(uuid4()), "expected_revision": run["revision"], "answer": "stale"},
    )
    assert response.status_code == 409
    assert (await client.post(root + "/resume")).status_code == 422
    assert not (await client.get(root + "/questions")).json()["items"][0]["answers"]


async def test_question_request_replay_and_answer_id_conflict(client, project, github):
    run = (await enroll(client, project)).json()
    root = f"/api/v1/pipeline-runs/{run['id']}"
    payload = {"request_id": str(uuid4()), "expected_revision": run["revision"], "question": "Keep the old API?"}
    q = (await client.post(root + "/questions", json=payload)).json()
    assert (await client.post(root + "/questions", json=payload)).json()["id"] == q["id"]
    assert (await client.post(root + "/questions", json=payload | {"question": "Different"})).status_code == 409
    _, ap = await answer(client, root, q)
    assert (
        await client.post(root + f"/questions/{q['id']}/answers", json=ap | {"answer": "Changed"})
    ).status_code == 409


async def test_old_resume_replay_does_not_unpause_a_later_stop(client, project, github):
    run = (await enroll(client, project)).json()
    root = f"/api/v1/pipeline-runs/{run['id']}"
    await client.post(root + "/pause")
    payload = {"request_id": str(uuid4()), "expected_revision": (await state(client, root))["revision"]}
    assert (await client.post(root + "/resume", json=payload)).status_code == 200
    paused = (await client.post(root + "/pause")).json()
    replay = await client.post(root + "/resume", json=payload)
    assert replay.status_code == 200
    assert replay.json()["state"] == "paused"
    assert replay.json()["revision"] == paused["revision"]
    assert (await client.get(root + "/attempts")).json()["total_count"] == 1


async def test_concurrent_answer_and_resume_are_single_requests(client, project, github, is_postgres):
    if not is_postgres:
        pytest.skip("Row lock concurrency requires PostgreSQL")
    run = (await enroll(client, project)).json()
    root = f"/api/v1/pipeline-runs/{run['id']}"
    question = (await ask(client, root)).json()
    payload = {
        "request_id": str(uuid4()),
        "expected_revision": (await state(client, root))["revision"],
        "answer": "Use the default",
    }
    answers = await asyncio.gather(
        *(client.post(root + f"/questions/{question['id']}/answers", json=payload) for _ in range(2))
    )
    assert all(a.status_code == 200 for a in answers), [a.text for a in answers]
    assert len({a.json()["id"] for a in answers}) == 1
    resume_payload = {
        "request_id": str(uuid4()),
        "expected_revision": (await state(client, root))["revision"],
        "answer_id": answers[0].json()["id"],
    }
    resumed = await asyncio.gather(*(client.post(root + "/resume", json=resume_payload) for _ in range(2)))
    assert all(a.status_code == 200 for a in resumed), [a.text for a in resumed]
    assert (await client.get(root + "/attempts")).json()["total_count"] == 1


async def test_agent_question_is_attempt_bound_and_delivery_failure_preserves_answer(
    client, project, mention_github, monkeypatch
):
    from app.features.project_management.pipeline_runs.usecases import delivery
    from app.features.project_management.pipelines.github import GitHubActionsReader

    run, attempt = await scenarios.prepare_run(client, project)
    root = f"/api/v1/pipeline-runs/{run['id']}"
    assert (await client.post(root + "/advance")).status_code == 200
    marker = {
        "attempt": attempt["request_snapshot"]["correlation_marker"],
        "head": scenarios.HEAD,
        "question": "Which empty-state behavior should be used?",
    }
    for index, author, question in (
        (101, "random-user", marker),
        (102, "chatgpt-codex-connector[bot]", marker | {"attempt": "hub-attempt:stale"}),
    ):
        mention_github.append(
            {
                "id": index,
                "body": "<!-- autohub-question " + json.dumps(question) + " -->",
                "created_at": (utc_now() + timedelta(seconds=1)).isoformat(),
                "user": {"login": author},
            }
        )
    assert (await client.post(root + "/advance")).json()["state"] == "implementing"
    assert (await client.get(root + "/questions")).json()["total_count"] == 0
    mention_github.append(
        {
            "id": 103,
            "body": "<!-- autohub-question " + json.dumps(marker) + " -->",
            "created_at": (utc_now() + timedelta(seconds=2)).isoformat(),
            "user": {"login": "chatgpt-codex-connector[bot]"},
        }
    )
    assert (await client.post(root + "/advance")).json()["state"] == "blocked"
    questions = (await client.get(root + "/questions")).json()["items"]
    assert len(questions) == 1
    assert questions[0]["execution_attempt_id"] == attempt["id"]
    saved, _ = await answer(client, root, questions[0])
    request = {
        "request_id": str(uuid4()),
        "expected_revision": (await state(client, root))["revision"],
        "answer_id": saved["id"],
    }
    assert (await client.post(root + "/resume", json=request)).status_code == 200

    async def stall(*args):
        await asyncio.Event().wait()

    with monkeypatch.context() as patched:
        patched.setattr(delivery, "DISPATCH_IO_SECONDS", 0.05)
        patched.setattr(GitHubActionsReader, "reconcile_issue_comment", stall)
        assert (await client.post(root + "/advance")).status_code == 504
    assert (await client.post(root + "/resume", json=request)).status_code == 200
    assert (await client.post(root + "/advance")).json()["state"] == "implementing"
    # Previously collected replies cannot block the new attempt again.
    assert (await client.post(root + "/advance")).json()["state"] == "implementing"
    attempts = (await client.get(root + "/attempts")).json()["items"]
    assert len(attempts) == 2
    assert "Show an empty list" in attempts[-1]["request_snapshot"]["instructions"]
    assert "Show an empty list" in mention_github[-1]["body"]
    deliveries = (await client.get(root + f"/attempts/{attempts[-1]['id']}/deliveries")).json()
    assert len(deliveries) == 1
    assert (await client.get(root + "/questions")).json()["total_count"] == 1
