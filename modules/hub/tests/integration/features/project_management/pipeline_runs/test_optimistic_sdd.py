"""Repository agents own SDD; ordinary PR input and GitHub facts own delivery."""

import json
from datetime import timedelta

import pytest
from app_testing_base import utc_now

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios
from tests.integration.features.project_management.pipeline_runs.test_interactions import answer, ask, state

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
github = scenarios.github
project = scenarios.project
mention_github = scenarios.mention_github
UNIT = "docs/proposals/PROP-example"


async def enroll_activity(client, project, github, **options):
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    assert changed.status_code == 200, changed.text
    github.pulls[7]["head"]["ref"] = "plan-example"
    github.pulls[7]["draft"] = True
    response = await client.post(
        f"/api/v1/projects/{project['id']}/runs",
        json={"pull_number": 7, "spec_dir": UNIT, "activity_effort": "high", **options},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_enrollment_has_only_descriptive_intent_and_no_repository_readiness(client, project, github):
    run = await enroll_activity(client, project, github)
    assert run["state"] == "queued" and run["sdd_progress"] is None
    assert run["sdd_snapshot"] == {
        "execution_version": 2,
        "provider": "repository-agent",
        "spec_dir": UNIT,
        "activity_kind": "plan",
        "handoff_pending": False,
        "activity_effort": "high",
    }
    assert all("/contents/" not in path and "/commits/" not in path for path in github.paths)
    root = f"/api/v1/pipeline-runs/{run['id']}"
    question = (await ask(client, root)).json()
    saved, _ = await answer(client, root, question)
    assert (await state(client, root))["state"] == "blocked"
    resumed = await client.post(
        root + "/resume",
        json={
            "request_id": "7b423e34-a370-482f-a0a0-4c379541dc33",
            "expected_revision": (await state(client, root))["revision"],
            "answer_id": saved["id"],
        },
    )
    assert resumed.status_code == 200, resumed.text
    [attempt] = (await client.get(root + "/attempts")).json()["items"]
    instructions = attempt["request_snapshot"]["instructions"]
    assert "repository and its working agent own" in instructions
    assert "Current workflow stage" not in instructions and "devkit sync" not in instructions
    assert "stop for the hub" not in instructions
    assert "Show an empty list" in instructions
    assert github.pulls[7]["draft"] is True


@pytest.mark.parametrize("during_ci", [False, True])
async def test_agent_question_after_push_pauses_before_ci_and_uses_current_head(
    client, project, github, mention_github, during_ci
):
    run = await enroll_activity(client, project, github)
    root = f"/api/v1/pipeline-runs/{run['id']}"
    started = await client.post(root + "/advance")
    assert started.status_code == 200 and started.json()["state"] == "implementing", started.text
    [attempt] = (await client.get(root + "/attempts")).json()["items"]
    github.pulls[7]["head"]["sha"] = "e" * 40
    if during_ci:
        progressed = await client.post(root + "/advance")
        assert progressed.status_code == 200 and progressed.json()["state"] == "awaiting_ci", progressed.text
    marker = {
        "attempt": attempt["request_snapshot"]["correlation_marker"],
        "head": scenarios.HEAD,
        "question": "Which repository option should be used?",
    }
    mention_github.append(
        {
            "id": 999,
            "body": "<!-- autohub-question " + json.dumps(marker) + " -->",
            "created_at": (utc_now() + timedelta(seconds=2)).isoformat(),
            "user": {"login": "chatgpt-codex-connector[bot]"},
        }
    )
    observed = await client.post(root + "/advance")
    assert observed.status_code == 200 and observed.json()["state"] == "blocked", observed.text
    [question] = (await client.get(root + "/questions")).json()["items"]
    assert question["head_sha"] == "e" * 40 and question["execution_attempt_id"] == attempt["id"]
    saved, _ = await answer(client, root, question)
    assert (await state(client, root))["state"] == "blocked"
    assert github.pulls[7]["draft"] is True
    resumed = await client.post(
        root + "/resume",
        json={
            "request_id": "7b423e34-a370-482f-a0a0-4c379541dc33",
            "expected_revision": (await state(client, root))["revision"],
            "answer_id": saved["id"],
        },
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["state"] == "dispatching"


async def test_direct_enrollment_cannot_steal_an_unsettled_activity_candidate(client, project, github, session):
    from uuid import UUID, uuid4

    from app.features.project_management.sdd.batch_models import SddActivityClaim

    claim = SddActivityClaim(
        project_id=UUID(project["id"]),
        request_id=uuid4(),
        actor="original",
        request_digest="original",
        unit=UNIT,
        activity="plan",
        checkpoint={"execution_version": 2, "uncertain": True, "pull_number": 7},
    )
    session.add(claim)
    await session.commit()
    github.paths.clear()
    refused = await scenarios.enroll(client, project)
    assert refused.status_code == 409 and str(claim.id) in refused.text, refused.text
    assert not github.paths
