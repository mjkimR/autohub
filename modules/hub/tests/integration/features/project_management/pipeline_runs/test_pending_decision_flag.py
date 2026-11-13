import pytest

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios
from tests.integration.features.project_management.pipeline_runs.test_interactions import ask, state

project = scenarios.project
github = scenarios.github
enroll = scenarios.enroll
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
URL = "/api/v1/pipeline-runs"


async def flags(client, **params):
    listed = (await client.get(URL, params={"limit": 1, **params})).json()
    return {row["id"]: row["has_pending_decision"] for row in listed["items"]}


async def test_run_reads_report_a_pending_decision_until_it_resolves(client, project, github):
    asked = (await enroll(client, project, 7)).json()
    quiet = (await enroll(client, project, 8)).json()
    assert asked["has_pending_decision"] is False
    root = f"{URL}/{asked['id']}"
    question = (await ask(client, root)).json()
    assert (await client.get(root)).json()["has_pending_decision"] is True
    assert (await client.get(f"{URL}/{quiet['id']}")).json()["has_pending_decision"] is False
    # Each run's flag holds on a one-row page, independent of any decisions page.
    assert await flags(client, pull_number=7) == {asked["id"]: True}
    assert await flags(client, pull_number=8) == {quiet["id"]: False}
    dismissed = await client.post(
        root + f"/questions/{question['id']}/dismiss",
        json={"expected_revision": (await state(client, root))["revision"], "reason": "Not needed"},
    )
    assert dismissed.status_code == 200
    assert (await client.get(root)).json()["has_pending_decision"] is False
    assert await flags(client, pull_number=7) == {asked["id"]: False}


async def test_flag_follows_the_projection_inside_one_transaction(client, project, github, session):
    from uuid import UUID, uuid4

    from app.features.project_management.pipeline_runs.models import PipelineRun, RunQuestion

    enrolled = (await enroll(client, project, 7)).json()
    run = await session.get(PipelineRun, UUID(enrolled["id"]))
    assert run.has_pending_decision is False
    run.state = "blocked"
    session.add(
        RunQuestion(
            id=uuid4(),
            pipeline_run_id=run.id,
            head_sha="c" * 40,
            question="Inside the flush",
            actor="test",
            source="operator",
            state="open",
        )
    )
    await session.flush()
    assert run.has_pending_decision is True
    run.state = "canceled"
    await session.flush()
    assert run.has_pending_decision is False
    await session.rollback()
