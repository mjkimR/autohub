"""Saved last-write clocks on Plan, Item and replacement owner transitions."""

from datetime import timedelta
from uuid import UUID

import pytest
from app.features.project_management.work_plans.models import WorkItem, WorkPlan
from app.features.project_management.work_plans.replacement_models import ReplacementLink
from tests.integration.common.test_timestamps import clock as clock
from tests.integration.common.test_timestamps import utc
from tests.integration.features.project_management.owed_items.test_owed_items import items as owed_items
from tests.integration.features.project_management.work_plans import test_replacements as replacements
from tests.integration.features.project_management.work_plans.test_work_plans import control, create, due, get, spec

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


def waiting(rows, subject):
    [row] = [r for r in rows if r["subject"]["id"] == str(subject)]
    return row["waiting_since"]


async def test_proposed_plan_owner_write_is_owed_last_write(client, setup_work, session, clock):
    project, _, _, _ = setup_work
    plan = await create(client, project, spec(state="draft"))
    created = await session.get(WorkPlan, UUID(plan["id"]), populate_existing=True)
    created_at = utc(created.created_at)
    await control(client, project, plan, "propose")
    await session.refresh(created)
    assert utc(created.updated_at) == clock[0]
    assert utc(created.created_at) == created_at
    assert waiting(await owed_items(client), created.id) == clock[0].isoformat().replace("+00:00", "Z")
    clock[0] += timedelta(hours=1)
    # A rejected stale revision must not alter the maintained owner time.
    response = await client.post(
        f"/api/v1/projects/{project['id']}/work-plans/{plan['id']}/control",
        json={"action": "draft", "expected_revision": plan["revision"]},
    )
    assert response.status_code == 409
    await session.refresh(created)
    assert utc(created.updated_at) == clock[0] - timedelta(hours=1)


async def test_item_observation_owner_write_drives_attention_waiting_since(client, setup_work, session, clock):
    project, github, worker, _ = setup_work
    plan = await create(client, project)
    await worker.advance_project(UUID(project["id"]))
    current = await get(client, project, plan)
    item = current["items"][0]
    # A changed PR identity drives the real observation owner to attention.
    item_model = await session.get(WorkItem, UUID(item["id"]), populate_existing=True)
    github.pulls[item_model.pull_number]["base"]["ref"] = "wrong-target"
    clock[0] += timedelta(hours=1)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    row = await session.get(WorkItem, UUID(item["id"]), populate_existing=True)
    assert row.state == "attention"
    assert utc(row.updated_at) == clock[0]
    assert waiting(await owed_items(client), row.id) == clock[0].isoformat().replace("+00:00", "Z")


async def test_replacement_link_owner_updates_and_withdrawal_maintain_time(client, setup_work, session, clock):
    _project, _, _, _original, _, root, read, _ = await replacements.fixture(client, setup_work, session)
    link_id = UUID(read["links"][0]["id"])
    row = await session.get(ReplacementLink, link_id, populate_existing=True)
    # The owner model's ordinary ORM write needs no explicit timestamp assignment.
    row.reason = "Updated retained replacement context"
    await session.commit()
    await session.refresh(row)
    assert utc(row.updated_at) == clock[0]
    assert waiting(await owed_items(client), row.id) == clock[0].isoformat().replace("+00:00", "Z")
    clock[0] += timedelta(hours=1)
    current = (await client.get(root)).json()
    command = replacements.command(current, current["links"][0]["current_replacement"])
    result = await client.post(root + f"/{link_id}/withdraw", json=command)
    assert result.status_code == 200, result.text
    await session.refresh(row)
    assert not row.active
    assert utc(row.updated_at) == clock[0]
    assert all(r["subject"]["id"] != str(link_id) for r in await owed_items(client))
