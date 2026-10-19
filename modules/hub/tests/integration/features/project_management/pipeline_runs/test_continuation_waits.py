"""Continuation clears obsolete waits and rechecks admission without duplicate delivery."""

import asyncio
import json
from uuid import UUID, uuid4

import httpx
import pytest
from app.common.config import get_github_webhook_config
from app.features.ai_catalogs.models import AICatalog
from app.features.ai_catalogs.services import AICatalogService
from app.features.execution.tasks.core.context import task_context
from app.features.execution.tasks.domains.pipeline.task import dispatch_project_task
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.projects.schemas import ProjectDispatchPayload
from app_layer_base.core.database.transaction import AsyncTransaction

from tests.integration.features.project_management.github_webhooks.test_github_webhooks_api import _headers
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import advance
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import github as github
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import run as run

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.mark.parametrize("entry", ["manual", "webhook"])
async def test_old_draft_wait_does_not_delay_ready_ci_repair(client, run, github, monkeypatch, entry):
    github.draft = True
    waiting = await advance(client, run)
    assert waiting["next_action_at"] is not None
    github.draft = False
    github.ci_conclusion = "failure"
    if entry == "manual":
        repaired = await advance(client, run)
    else:
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhook-test-secret")
        monkeypatch.delenv("WEBHOOK_TASK_QUEUE", raising=False)
        get_github_webhook_config.cache_clear()
        body = json.dumps(
            {"repository": {"full_name": "owner/app"}, "pull_request": {"number": 7}, "action": "ready_for_review"}
        ).encode()
        try:
            response = await client.post(
                "/api/github/webhooks",
                content=body,
                headers=_headers(body, delivery=str(uuid4()), event="pull_request"),
            )
            assert response.status_code == 202
            repaired = (await client.get(f"/api/v1/pipeline-runs/{run['id']}")).json()
        finally:
            get_github_webhook_config.cache_clear()
    assert repaired["state"] == "implementing", repaired
    assert repaired["next_action_at"] is None
    assert len(github.comments) == 1


@pytest.mark.parametrize("release_capacity", [True, False])
async def test_capacity_released_in_observation_allows_repair_this_tick(
    client, run, github, session, monkeypatch, credential_key_provider, is_postgres, release_capacity
):
    if not is_postgres:
        pytest.skip("Concurrent admission and observation need independent PostgreSQL transactions")

    def respond(request):
        if request.url.path.endswith("/pulls/8"):
            return httpx.Response(200, json={**github.pull(), "number": 8})
        return github.respond(request)

    monkeypatch.setattr(
        "app.features.project_management.pipelines.services.create_github_client",
        lambda token: httpx.AsyncClient(base_url="https://api.github.com", transport=httpx.MockTransport(respond)),
    )
    second = await client.post(
        f"/api/v1/projects/{run['project_id']}/runs", json={"pull_number": 8, "implemented": True}
    )
    assert second.status_code == 201, second.text
    first_id, second_id = UUID(run["id"]), UUID(second.json()["id"])
    second_run = await session.get(PipelineRun, second_id)
    second_run.state = "implementing"
    catalog = await session.get(AICatalog, second_run.ai_catalog_id)
    catalog.configured_concurrency = 1
    await session.commit()
    github.ci_conclusion = "failure"
    rejected = asyncio.Event()
    original_dispatch = AICatalogService.request_dispatch
    original_observe = PipelineRunUseCase.observe_run
    admissions = 0

    async def admission(self, *args, **kwargs):
        nonlocal admissions
        admissions += 1
        result = await original_dispatch(self, *args, **kwargs)
        if result.rejection:
            assert "concurrency limit" in result.rejection
            rejected.set()
        return result

    async def observe(self, run_id, **kwargs):
        if run_id != second_id:
            return await original_observe(self, run_id, **kwargs)
        await asyncio.wait_for(rejected.wait(), timeout=10)
        async with AsyncTransaction() as tx:
            saved = await tx.get(PipelineRun, second_id)
            assert saved is not None
            saved.state = "completed" if release_capacity else "implementing"
            saved.revision += 1
            await tx.flush()
            return PipelineRunRead.model_validate(saved)

    monkeypatch.setattr(AICatalogService, "request_dispatch", admission)
    monkeypatch.setattr(PipelineRunUseCase, "observe_run", observe)
    monkeypatch.setattr(
        "app.features.execution.tasks.domains.pipeline.task.get_credential_key_provider",
        lambda: credential_key_provider,
    )
    with task_context(config_id=uuid4(), config_name="test", run_id=uuid4()):
        await dispatch_project_task(ProjectDispatchPayload(project_id=UUID(run["project_id"])))
    assert rejected.is_set()
    result = (await client.get(f"/api/v1/pipeline-runs/{first_id}")).json()
    completed = (await client.get(f"/api/v1/pipeline-runs/{second_id}")).json()
    assert completed["state"] == ("completed" if release_capacity else "implementing")
    assert result["state"] == ("implementing" if release_capacity else "dispatching"), result
    assert len(github.comments) == int(release_capacity)
    assert admissions == 2


async def test_quota_hold_after_observation_is_not_retried(
    client, run, github, session, monkeypatch, credential_key_provider
):
    saved = await session.get(PipelineRun, UUID(run["id"]))
    catalog = await session.get(AICatalog, saved.ai_catalog_id)
    catalog.availability_state = "quota_blocked"
    catalog.available_at = None
    await session.commit()
    github.ci_conclusion = "failure"
    original_dispatch = AICatalogService.request_dispatch
    admissions = 0

    async def admission(self, *args, **kwargs):
        nonlocal admissions
        admissions += 1
        return await original_dispatch(self, *args, **kwargs)

    monkeypatch.setattr(AICatalogService, "request_dispatch", admission)
    monkeypatch.setattr(
        "app.features.execution.tasks.domains.pipeline.task.get_credential_key_provider",
        lambda: credential_key_provider,
    )
    with task_context(config_id=uuid4(), config_name="test", run_id=uuid4()):
        await dispatch_project_task(ProjectDispatchPayload(project_id=UUID(run["project_id"])))
    result = (await client.get(f"/api/v1/pipeline-runs/{run['id']}")).json()
    assert result["state"] == "dispatching"
    assert admissions == 1
    assert github.comments == []
