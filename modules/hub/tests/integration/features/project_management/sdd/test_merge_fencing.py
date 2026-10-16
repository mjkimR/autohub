"""A stop winning the final native PR read must fence the merge write."""

import pytest
from app.features.project_management.pipeline_runs.usecases.progress import PipelineRunProgress
from app.features.project_management.pipelines.services import PipelineObservationService
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import advance
from tests.integration.features.project_management.sdd import test_native as scenarios

github = scenarios.github
project = scenarios.project
inspector = scenarios.inspector
run = scenarios.run
unit_branch = scenarios.unit_branch
decide = scenarios.decide

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.mark.parametrize("action", ["pause", "cancel", "revoke"])
async def test_stop_during_native_merge_authorization_prevents_write(client, run, github, monkeypatch, action):
    waiting = await advance(client, run)
    approved, _ = await decide(client, waiting, "approve")
    assert approved.status_code == 200
    github.draft = False
    integrated = await advance(client, run)
    assert integrated["state"] == "awaiting_ci"
    in_authorization = False
    authorizations = 0
    interrupted = False
    original_authorize = PipelineRunProgress._authorize_merge
    original_pull = PipelineObservationService.get_pull_request

    async def authorize(self, checkpoint):
        nonlocal in_authorization, authorizations
        authorizations += 1
        in_authorization = True
        try:
            return await original_authorize(self, checkpoint)
        finally:
            in_authorization = False

    async def get_pull(self, *args, **kwargs):
        nonlocal interrupted
        if in_authorization and authorizations == 2 and not interrupted:
            interrupted = True
            if action == "revoke":
                paused, _ = await decide(client, integrated, "revoke")
            else:
                paused = await client.post(f"/api/v1/pipeline-runs/{run['id']}/{action}")
            assert paused.status_code == 200, paused.text
        return await original_pull(self, *args, **kwargs)

    monkeypatch.setattr(PipelineRunProgress, "_authorize_merge", authorize)
    monkeypatch.setattr(PipelineObservationService, "get_pull_request", get_pull)
    response = await client.post(f"/api/v1/pipeline-runs/{run['id']}/advance")
    assert interrupted
    assert github.merge_requests == 0, f"merge_requests={github.merge_requests}; advance_status={response.status_code}"
