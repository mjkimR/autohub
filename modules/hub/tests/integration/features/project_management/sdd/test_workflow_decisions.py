from uuid import uuid4

import pytest
from app.features.project_management.sdd import services
from tests.integration.features.project_management.pipeline_runs import test_merge_stage as merge
from tests.integration.features.project_management.sdd import test_native as native
from tests.integration.features.project_management.sdd.test_native import (
    decide,
    evidence,
)

github = native.github
project = native.project
inspector = native.inspector
run = native.run
from tests.integration.features.project_management.sdd import test_hitl

delivery = test_hitl.delivery

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.mark.parametrize("action,value", [("accept", "direct"), ("decline", None), ("cancel", None)])
async def test_workflow_answer_is_revision_fenced_durable_and_replayed_once(
    client, run, monkeypatch, action, value, delivery
):
    async def inspect(self, repository, spec_dir, pull, token, **kwargs):
        result = evidence(pull["head"]["sha"], pull["base"]["sha"])
        result["current"]["stage"] = None
        result["current"]["requests"] = [
            {
                "id": "handoff",
                "kind": "choose",
                "title": "Choose",
                "prompt": "Choose workflow",
                "options": [{"id": "direct", "eligible": True, "description": "", "recommended": True}],
            }
        ]
        if op := kwargs.get("operation"):
            result["prepared_record"] = {
                "id": op["id"],
                "file": "decisions/01-handoff.yaml",
                "content": "fixture",
                "operation": op,
            }
        return result

    monkeypatch.setattr(services.SddService, "inspect", inspect)
    waiting = await merge.advance(client, run)
    assert waiting["state"] == "blocked"
    answer = {"request": "handoff", "action": action, "value": value}
    result, body = await decide(client, waiting, workflow_answer=answer)
    assert result.status_code == 200, result.text
    assert result.json()["state"] == "dispatching"
    assert result.json()["sdd_progress"]["decision_records"][0]["operation"]["action"] == action
    replay = await client.post(f"/api/v1/pipeline-runs/{run['id']}/resume", json=body)
    assert replay.json()["revision"] == result.json()["revision"]
    stale = await client.post(f"/api/v1/pipeline-runs/{run['id']}/resume", json={**body, "request_id": str(uuid4())})
    assert stale.status_code == 409
    records = (await client.get(f"/api/v1/pipeline-runs/{run['id']}/sdd-decisions")).json()
    assert records[0]["workflow_answer"] == answer
    assert not result.json()["sdd_progress"].get("approval")
    publishing = await merge.advance(client, result.json())
    assert publishing["state"] == "implementing"
    publishing = await merge.advance(client, publishing)
    assert publishing["state"] == "implementing"
    assert publishing["sdd_progress"]["decision_head"] == publishing["sdd_progress"]["head_sha"]
