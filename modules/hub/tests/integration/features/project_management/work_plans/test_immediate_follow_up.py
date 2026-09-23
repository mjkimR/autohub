from uuid import UUID, uuid4

import pytest
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.work_plans.kick import WorkPlanKick
from tests.integration.features.project_management.work_plans.conftest import LIVE_KICK, _tick_only
from tests.integration.features.project_management.work_plans.test_work_plans import control, create, get

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


def lifecycle(worker):
    return PipelineRunUseCase(repo=None, projects=None, observer=worker.observer)  # type: ignore[arg-type]


async def test_registration_starts_ready_items_without_waiting_for_a_tick(client, setup_work, live_kick):
    project, github, _, _ = setup_work
    plan = await create(client, project)

    first, second = plan["items"]
    assert first["state"] == "running" and first["pull_url"] and second["state"] == "waiting"
    assert len(github.pulls) == 1
    live_kick.assert_awaited_once()
    assert live_kick.await_args.args[0] == UUID(first["pipeline_run_id"])


async def test_a_merge_releases_dependents_ahead_of_the_polling_cadence(client, setup_work, live_kick):
    project, github, worker, _ = setup_work
    plan = await create(client, project)
    first = plan["items"][0]
    github.merge(100)

    # The item was just observed, so the tick would skip it for a minute; the merge event must not wait.
    await WorkPlanKick(lifecycle(worker)).run(UUID(project["id"]), run_id=UUID(first["pipeline_run_id"]))

    first, second = (await get(client, project, plan))["items"]
    assert first["state"] == "succeeded" and first["merge_sha"]
    assert second["state"] == "running" and len(github.pulls) == 2
    assert live_kick.await_args.args[0] == UUID(second["pipeline_run_id"])


async def test_an_unrelated_run_starts_nothing(client, setup_work, live_kick, monkeypatch):
    project, github, worker, _ = setup_work
    monkeypatch.setattr(WorkPlanKick, "run", _tick_only)
    plan = await create(client, project, SINGLE)
    monkeypatch.setattr(WorkPlanKick, "run", LIVE_KICK)
    kick = WorkPlanKick(lifecycle(worker))

    # Every webhook for a non-work run passes through; it must not become a project-wide tick.
    await kick.run(UUID(project["id"]), run_id=uuid4())
    assert (await get(client, project, plan))["items"][0]["state"] == "waiting" and not github.pulls

    await kick.run(UUID(project["id"]))
    assert (await get(client, project, plan))["items"][0]["state"] == "running"


async def test_pause_is_not_a_trigger_and_resume_starts_immediately(client, setup_work, live_kick, monkeypatch):
    project, github, _, _ = setup_work
    monkeypatch.setattr(WorkPlanKick, "run", _tick_only)
    plan = await create(client, project, SINGLE)
    monkeypatch.setattr(WorkPlanKick, "run", LIVE_KICK)

    paused = await control(client, project, plan, "pause")
    assert paused["items"][0]["state"] == "waiting" and not github.pulls

    resumed = await control(client, project, paused, "resume")
    assert resumed["state"] == "active" and resumed["items"][0]["state"] == "running"
    live_kick.assert_awaited_once()


SINGLE = {
    "title": "Single",
    "items": [{"key": "a", "title": "Only", "description": "Do it", "acceptance": "Checks pass"}],
}
