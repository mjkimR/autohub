"""A detected push continues through CI in one advance, stopping at real waits."""

import json
from uuid import UUID, uuid4

import pytest
from app.common.config import get_github_webhook_config
from app.features.execution.tasks.core.context import task_context
from app.features.execution.tasks.domains.pipeline.task import dispatch_project_task
from app.features.project_management.pipeline_runs.models import ExecutionAttempt, ExecutionDelivery, PipelineRun
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.schemas import ProjectDispatchPayload
from app_testing_base import utc_now
from sqlalchemy import select

from tests.integration.features.project_management.github_webhooks.test_github_webhooks_api import _headers
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import advance
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import github as github
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import run as run

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.mark.parametrize(
    ("ci", "draft", "expected"),
    [
        ("success", False, "completed"),
        ("failure", False, "implementing"),
        ("missing", False, "awaiting_ci"),
        ("success", True, "awaiting_ci"),
    ],
)
@pytest.mark.parametrize("entry", ["manual", "tick", "webhook"])
async def test_push_continues_to_ci_without_polling(
    client, run, github, session, monkeypatch, credential_key_provider, ci, draft, expected, entry
):
    saved = await session.get(PipelineRun, UUID(run["id"]))
    attempt = await session.scalar(select(ExecutionAttempt).where(ExecutionAttempt.pipeline_run_id == saved.id))
    snapshot = dict(attempt.request_snapshot)
    snapshot["pull_request"] = {**snapshot["pull_request"], "head_sha": "a" * 40}
    attempt.request_snapshot, attempt.request_digest = snapshot, request_digest(snapshot)
    attempt.state, saved.state = "running", "implementing"
    session.add(ExecutionDelivery(execution_attempt_id=attempt.id, delivery_number=1, posted_at=utc_now()))
    await session.commit()
    github.ci_conclusion, github.has_ci, github.draft = ci, ci != "missing", draft
    calls = 0
    original = PipelineObservationService.observe

    async def observe(self, config):
        nonlocal calls
        calls += 1
        return await original(self, config)

    monkeypatch.setattr(PipelineObservationService, "observe", observe)
    if entry == "manual":
        result = await advance(client, run)
    else:
        if entry == "tick":
            monkeypatch.setattr(
                "app.features.execution.tasks.domains.pipeline.task.get_credential_key_provider",
                lambda: credential_key_provider,
            )
            with task_context(config_id=uuid4(), config_name="test", run_id=uuid4()):
                await dispatch_project_task(ProjectDispatchPayload(project_id=UUID(run["project_id"])))
        else:
            monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhook-test-secret")
            monkeypatch.delenv("WEBHOOK_TASK_QUEUE", raising=False)
            get_github_webhook_config.cache_clear()
            body = json.dumps(
                {"repository": {"full_name": "owner/app"}, "pull_request": {"number": 7}, "action": "synchronize"},
                separators=(",", ":"),
            ).encode()
            headers = _headers(body, delivery=str(uuid4()), event="pull_request")
            try:
                response = await client.post("/api/github/webhooks", content=body, headers=headers)
                assert response.status_code == 202
                duplicate = await client.post("/api/github/webhooks", content=body, headers=headers)
                assert duplicate.json() == {"status": "duplicate"}
            finally:
                get_github_webhook_config.cache_clear()
        result = (await client.get(f"/api/v1/pipeline-runs/{run['id']}")).json()

    assert result["state"] == expected
    assert calls == 1
    assert github.merge_requests == int(expected == "completed")
    assert len(github.comments) == int(ci == "failure")
    if draft:
        assert result["next_action_at"] is not None
        assert "Waiting for approval" in result["pause_reason"]
