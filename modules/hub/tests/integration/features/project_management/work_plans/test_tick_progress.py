"""A scheduler tick starts newly admitted work and dependents of confirmed merges."""

import json
from uuid import UUID, uuid4

import httpx
import pytest
from app.features.execution.tasks.core.context import task_context
from app.features.execution.tasks.domains.pipeline.task import dispatch_project_task
from app.features.project_management.projects.schemas import ProjectDispatchPayload
from app_testing_base import utc_now
from tests.integration.features.project_management.work_plans.test_work_plans import create, due, get

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_tick_prepares_and_dispatches_new_work_and_merged_dependents(
    client, setup_work, session, monkeypatch, credential_key_provider
):
    project, github, _, _ = setup_work
    monkeypatch.setattr(
        "app.features.execution.tasks.domains.pipeline.task.get_credential_key_provider",
        lambda: credential_key_provider,
    )
    original = github.respond
    comments = {}

    def respond(request):
        if request.url.path.endswith("/comments"):
            thread = comments.setdefault(request.url.path, [])
            if request.method == "POST":
                thread.append(
                    {
                        "id": len(comments) * 100 + len(thread),
                        "body": json.loads(request.content)["body"],
                        "created_at": utc_now().isoformat(),
                        "user": {"login": "operator"},
                    }
                )
                return httpx.Response(201, json=thread[-1])
            return httpx.Response(200, json=thread)
        return original(request)

    monkeypatch.setattr(github, "respond", respond)
    plan = await create(client, project)

    async def tick():
        with task_context(config_id=uuid4(), config_name="test", run_id=uuid4()):
            await dispatch_project_task(ProjectDispatchPayload(project_id=UUID(project["id"])))

    await tick()
    first, second = (await get(client, project, plan))["items"]
    assert second["state"] == "waiting"
    first_run = (await client.get(f"/api/v1/pipeline-runs/{first['pipeline_run_id']}")).json()
    assert first_run["state"] == "implementing"
    assert sum(map(len, comments.values())) == 1

    github.merge(100)
    await due(session)
    await tick()
    first, second = (await get(client, project, plan))["items"]
    assert first["state"] == "succeeded"
    second_run = (await client.get(f"/api/v1/pipeline-runs/{second['pipeline_run_id']}")).json()
    assert second_run["state"] == "implementing"
    assert sum(map(len, comments.values())) == 2

    await tick()
    assert sum(map(len, comments.values())) == 2
