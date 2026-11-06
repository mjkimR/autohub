"""Project access and refusal precede preview evaluation at the real HTTP/DB boundary."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.features.project_management.sdd import milestones

from tests.integration.features.project_management.pipeline_runs import test_merge_stage as merge
from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
github = merge.github
project = scenarios.project


async def test_non_sdd_or_missing_project_refuses_before_preview(client, project, monkeypatch):
    evaluator = AsyncMock(side_effect=AssertionError("Must refuse before repository/runtime evaluation"))
    monkeypatch.setattr(milestones, "preview_milestone", evaluator)
    payload = {"ref": "main", "milestone_id": "MS-demo"}
    response = await client.post(f"/api/v1/projects/{project['id']}/sdd/milestone-preview", json=payload)
    assert response.status_code == 422
    response = await client.post(f"/api/v1/projects/{uuid4()}/sdd/milestone-preview", json=payload)
    assert response.status_code == 404
    evaluator.assert_not_called()


async def test_preview_response_is_observation_and_creates_no_run(client, project, monkeypatch):
    updated = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    assert updated.status_code == 200
    evaluator = AsyncMock(
        return_value={
            "project_id": project["id"],
            "repository": "owner/repo",
            "requested_ref": "main",
            "resolved_sha": "a" * 40,
            "milestone": {"id": "MS-demo"},
            "observed_at": "2026-11-05T00:00:00Z",
            "runtime_identity": "fixture",
            "complete": True,
            "counts": {"members": 0},
            "limits": {"members": 50},
            "reasons": [],
            "warnings": [],
            "nodes": [],
            "edges": [],
            "members": [],
        }
    )
    monkeypatch.setattr(milestones, "preview_milestone", evaluator)
    response = await client.post(
        f"/api/v1/projects/{project['id']}/sdd/milestone-preview", json={"ref": "main", "milestone_id": "MS-demo"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["resolved_sha"] == "a" * 40
    assert "execution_token" not in response.json()
    runs = await client.get("/api/v1/pipeline-runs", params={"project_id": project["id"]})
    assert runs.status_code == 200
    assert not runs.json()["items"]
