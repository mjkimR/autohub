from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.auth import MCP_READ, MCP_WRITE
from app.features.project_management.sdd import milestones
from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as runs
from tests.integration.features.project_management.sdd import test_batches as batches
from tests.integration.features.project_management.work_plans import conftest as work
from tests.integration.features.project_management.work_plans import test_item_recovery as recovery
from tests.integration.features.project_management.work_plans import test_replacements as replacement
from tests.integration.mcp import test_mcp as mcp

transport = mcp.transport
key = mcp.key
project = runs.project
github = runs.github
setup_work = work.setup_work
batch_head = batches.batch_head
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
READS = {
    "decisions_list",
    "runs_decision_outcome",
    "sdd_batches_list",
    "sdd_batches_get",
    "work_items_recoveries",
    "work_items_replacements",
}
WRITES = {
    "decisions_review",
    "sdd_batches_control",
    "work_items_recover",
    "work_items_replacement_link",
    "work_items_replacement_accept",
    "work_items_replacement_withdraw",
}


async def test_delivery_inventory_scope_and_invalid_inputs(client, key):
    tools = (await mcp.rpc(client, key, "tools/list")).json()["result"]["tools"]
    names = {t["name"] for t in tools}
    assert names >= READS | WRITES
    _, reader = await mcp.issue(client, [MCP_READ])
    _, writer = await mcp.issue(client, [MCP_WRITE])
    # Registry rejects scopes before owner handler (and before argument validation).
    for name in WRITES:
        result = await mcp.call(client, reader["key"], name, {}, error=True)
        assert result["error"]["code"] == "MCP_FORBIDDEN"
    for name in READS:
        result = await mcp.call(client, writer["key"], name, {}, error=True)
        assert result["error"]["code"] == "MCP_FORBIDDEN"
    assert (await mcp.call(client, key, "decisions_list", {"limit": 101}, error=True))["error"][
        "code"
    ] == "MCP_INVALID_ARGUMENTS"
    assert (await mcp.call(client, key, "decisions_list", {"actor": "spoof"}, error=True))["error"][
        "code"
    ] == "MCP_INVALID_ARGUMENTS"


async def test_exact_discovery_review_outcome_and_refusal(client, key, project, github):
    run = (await runs.enroll(client, project)).json()
    request_id = str(uuid4())
    root = f"/api/v1/pipeline-runs/{run['id']}"
    question = (
        await client.post(
            root + "/questions",
            json={"request_id": request_id, "expected_revision": run["revision"], "question": "Choose behavior"},
        )
    ).json()
    github.paths.clear()
    listing = (await mcp.call(client, key, "decisions_list", {"project_id": project["id"]}))["result"]
    entry = listing["items"][0]
    assert entry["subject_id"] == question["id"] and not github.paths
    args = {"key": entry["key"], "fingerprint": entry["fingerprint"]}
    reviewed = (await mcp.call(client, key, "decisions_review", args))["result"]
    assert reviewed["run_id"] == run["id"] and "sdd_progress" not in reviewed
    assert (await mcp.call(client, key, "decisions_review", args | {"fingerprint": "old"}, error=True))["error"][
        "code"
    ] == "CONFLICT"
    data = {"run_id": run["id"], "request_id": request_id, "operation": "question"}
    known = (await mcp.call(client, key, "runs_decision_outcome", data))["result"]
    assert known["record_state"] == "recorded" and "answer_text" not in known
    assert (await mcp.call(client, key, "runs_decision_outcome", data | {"operation": "answer"}))["result"][
        "record_state"
    ] == "unknown"
    assert (await mcp.call(client, key, "runs_decision_outcome", data | {"run_id": str(uuid4())}, error=True))["error"][
        "code"
    ] == "NOT_FOUND"
    assert not github.paths


async def test_batch_control_owner_replay_and_projection(client, key, project, monkeypatch, batch_head):
    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    monkeypatch.setattr(milestones, "preview_milestone", AsyncMock(return_value=batches.preview(project["id"])))
    response = await client.post(f"/api/v1/projects/{project['id']}/sdd/batches", json=batches.payload())
    assert response.status_code == 201, response.text
    row = response.json()
    ids = {"project_id": project["id"], "batch_id": row["id"]}
    assert (await mcp.call(client, key, "sdd_batches_list", {"project_id": project["id"]}))["result"]["items"][0][
        "id"
    ] == row["id"]
    view = (await mcp.call(client, key, "sdd_batches_get", ids))["result"]
    assert "basis" not in view and "initial" not in view["members"][0]
    args = ids | {"control": {"request_id": str(uuid4()), "expected_revision": row["revision"], "action": "pause"}}
    first = (await mcp.call(client, key, "sdd_batches_control", args))["result"]
    assert first["state"] == "paused"
    assert (await mcp.call(client, key, "sdd_batches_control", args))["result"]["revision"] == first["revision"]
    _, other = await mcp.issue(client, [MCP_WRITE])
    assert (await mcp.call(client, other["key"], "sdd_batches_control", args, error=True))["error"][
        "code"
    ] == "CONFLICT"
    assert (
        await mcp.call(
            client, key, "sdd_batches_control", args | {"control": args["control"] | {"action": "stop"}}, error=True
        )
    )["error"]["code"] == "CONFLICT"


async def test_recovery_machine_replay_and_safe_history(client, key, setup_work):
    project, _, _, plan, item = await recovery.failed_preparation(client, setup_work)
    ids = {"project_id": project["id"], "plan_id": plan["id"], "item_id": item["id"]}
    args = ids | {"recovery": recovery.command(plan, item)}
    first = (await mcp.call(client, key, "work_items_recover", args))["result"]
    assert first["recovery"]["actor"].startswith("machine:")
    assert "command" not in first["recovery"] and "prior_outcome" not in first["recovery"]
    assert (await mcp.call(client, key, "work_items_recover", args))["result"]["recovery"]["id"] == first["recovery"][
        "id"
    ]
    history = (await mcp.call(client, key, "work_items_recoveries", ids))["result"]
    assert history["total_count"] == 1 and "evidence" not in history["items"][0]["events"][0]
    _, other = await mcp.issue(client, [MCP_WRITE])
    assert (await mcp.call(client, other["key"], "work_items_recover", args, error=True))["error"][
        "code"
    ] == "RECOVERY_IDENTITY_CONFLICT"


async def test_replacement_accept_withdraw_machine_receipts(client, key, setup_work, session):
    project, _, _, original, _, _root, read, _ = await replacement.fixture(client, setup_work, session)
    ids = {"project_id": project["id"], "plan_id": original["id"], "item_id": original["items"][0]["id"]}
    view = (await mcp.call(client, key, "work_items_replacements", ids))["result"]
    assert "description" not in view["original"]
    args = ids | {"link_id": read["links"][0]["id"], "command": replacement.accept_command(read, original["items"][1])}
    accepted = (await mcp.call(client, key, "work_items_replacement_accept", args))["result"]
    assert accepted["links"][0]["acceptances"][0]["actor"].startswith("machine:")
    assert (await mcp.call(client, key, "work_items_replacement_accept", args))["result"]["result"] == accepted[
        "result"
    ]
    withdrawn = ids | {
        "link_id": args["link_id"],
        "command": replacement.command(accepted, accepted["links"][0]["current_replacement"])
        | {"acceptance_id": accepted["result"]["acceptance_id"]},
    }
    result = (await mcp.call(client, key, "work_items_replacement_withdraw", withdrawn))["result"]
    assert not result["links"][0]["acceptances"][0]["active"]
    assert (await mcp.call(client, key, "work_items_replacement_withdraw", withdrawn))["result"]["result"] == result[
        "result"
    ]
    _, other = await mcp.issue(client, [MCP_WRITE])
    assert (await mcp.call(client, other["key"], "work_items_replacement_withdraw", withdrawn, error=True))["error"][
        "code"
    ] == "REPLACEMENT_IDENTITY_CONFLICT"


async def test_replacement_link_replay_exact_machine(client, key, setup_work):
    from tests.integration.features.project_management.work_plans.test_work_plans import create, spec

    project, github, _, original, item = await recovery.failed_preparation(client, setup_work)
    github.refs["main"] = "a" * 40
    candidate = await create(
        client, project, spec(state="paused", items=[spec()["items"][0] | {"key": "new-candidate"}])
    )
    ids = {"project_id": project["id"], "plan_id": original["id"], "item_id": item["id"]}
    read = (
        await mcp.call(
            client, key, "work_items_replacements", ids | {"replacement_item_id": candidate["items"][0]["id"]}
        )
    )["result"]
    args = ids | {
        "command": replacement.command(read, read["candidate"]) | {"replacement_item_id": read["candidate"]["item_id"]}
    }
    first = (await mcp.call(client, key, "work_items_replacement_link", args))["result"]
    assert first["links"][0]["actor"].startswith("machine:")
    assert (await mcp.call(client, key, "work_items_replacement_link", args))["result"]["result"] == first["result"]
    assert (
        await mcp.call(
            client,
            key,
            "work_items_replacement_link",
            args | {"command": args["command"] | {"reason": "changed"}},
            error=True,
        )
    )["error"]["code"] == "REPLACEMENT_IDENTITY_CONFLICT"


async def test_replacement_full_history_page_retains_every_identity(client, key, setup_work, session, monkeypatch):
    from copy import deepcopy

    from app.features.project_management.work_plans.replacement_schemas import ReplacementRead
    from app.features.project_management.work_plans.replacement_usecase import ReplacementUseCase

    project, _, _, original, _, _, read, _ = await replacement.fixture(client, setup_work, session)
    active = read["links"][0]
    history = [deepcopy(active) | {"id": str(uuid4()), "active": False} for _ in range(101)]

    async def owner_get(self, project_id, plan_id, item_id, candidate, offset, limit, event_link_id, event_offset):
        return ReplacementRead.model_validate(
            read
            | {
                "links": [active, *history[offset : offset + limit]],
                "history_offset": offset,
                "history_total_count": len(history),
                "history_limit": limit,
            }
        )

    monkeypatch.setattr(ReplacementUseCase, "get", owner_get)
    args = {"project_id": project["id"], "plan_id": original["id"], "item_id": original["items"][0]["id"], "limit": 100}
    first = (await mcp.call(client, key, "work_items_replacements", args))["result"]
    assert first["history_limit"] == 99
    assert len(first["links"]) == 100 and first["links"][0]["active"]
    second = (await mcp.call(client, key, "work_items_replacements", args | {"offset": first["history_limit"]}))[
        "result"
    ]
    got = [link["id"] for page in (first, second) for link in page["links"] if not link["active"]]
    assert got == [link["id"] for link in history]
