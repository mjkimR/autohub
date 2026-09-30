from uuid import uuid4

import pytest
from app.auth import MCP_READ
from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as runs
from tests.integration.features.project_management.work_plans import conftest as work
from tests.integration.features.project_management.work_plans.test_registration import payload
from tests.integration.mcp import test_mcp as mcp

transport = mcp.transport
key = mcp.key
setup_work = work.setup_work
github = runs.github
project = runs.project

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_mcp_register_recover_and_control_plan(client, key, setup_work):
    project, github, _, _ = setup_work
    data = {"project_id": project["id"], "plan": payload()}
    _, reader = await mcp.issue(client, [MCP_READ])
    denied = await mcp.call(client, reader["key"], "work_plans_register", data, error=True)
    assert denied["error"]["code"] == "MCP_FORBIDDEN"
    invalid = data | {"plan": data["plan"] | {"items": [data["plan"]["items"][1]]}}
    assert not (await mcp.call(client, key, "work_plans_register", invalid, error=True))["ok"]
    assert github.requests == []
    plan = (await mcp.call(client, key, "work_plans_register", data))["result"]
    assert len(plan["items"]) == 2
    replay = (await mcp.call(client, key, "work_plans_register", data))["result"]
    assert replay["id"] == plan["id"]
    recovered = (
        await mcp.call(
            client, key, "work_plans_get", {"project_id": project["id"], "request_id": data["plan"]["request_id"]}
        )
    )["result"]
    assert recovered["id"] == plan["id"]
    conflict = await mcp.call(
        client, key, "work_plans_register", data | {"plan": data["plan"] | {"title": "Different"}}, error=True
    )
    assert conflict["error"]["code"] == "CONFLICT"
    args = {"project_id": project["id"], "plan_id": plan["id"]}
    for action in ("pause", "resume", "revoke"):
        plan = (
            await mcp.call(
                client,
                key,
                "work_plans_control",
                args | {"control": {"action": action, "expected_revision": plan["revision"]}},
            )
        )["result"]
    assert plan["state"] == "revoked"
    assert (await mcp.call(client, key, "work_plans_list", {"project_id": project["id"]}))["result"]["total_count"] == 1


async def test_mcp_answer_does_not_resume_and_replay_keeps_one_attempt(client, key, project):
    run = (await runs.enroll(client, project)).json()
    args = {"run_id": run["id"]}
    question = (
        await mcp.call(
            client,
            key,
            "runs_ask",
            args
            | {
                "question": {
                    "request_id": str(uuid4()),
                    "expected_revision": run["revision"],
                    "question": "Keep existing behavior?",
                }
            },
        )
    )["result"]
    _, reader = await mcp.issue(client, [MCP_READ])
    history = (await mcp.call(client, reader["key"], "runs_questions", args))["result"]
    response = {"request_id": str(uuid4()), "expected_revision": history["run_revision"], "answer": "Yes"}
    call_args = args | {"question_id": question["id"], "response": response}
    assert not (await mcp.call(client, reader["key"], "runs_answer", call_args, error=True))["ok"]
    saved = (await mcp.call(client, key, "runs_answer", call_args))["result"]
    assert saved["actor"].startswith("machine:")
    assert (await mcp.call(client, key, "runs_answer", call_args))["result"]["id"] == saved["id"]
    blocked = (await mcp.call(client, key, "runs_get", args))["result"]
    assert blocked["state"] == "blocked"
    resume = args | {"request_id": str(uuid4()), "expected_revision": blocked["revision"], "answer_id": saved["id"]}
    assert (await mcp.call(client, key, "runs_resume", resume))["result"]["state"] == "dispatching"
    assert (await mcp.call(client, key, "runs_resume", resume))["ok"]
    assert (await mcp.call(client, key, "runs_attempts", args))["result"]["total_count"] == 1
