from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.features.ai_catalogs.models import AICatalog
from app.features.project_management.agent_schedules.models import ProjectAgentSchedule
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.projects.models import Project
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from sqlalchemy import event
from sqlalchemy.engine import Engine

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def seed(session):
    p, other = Project(name="Owner project"), Project(name="Other project")
    catalog = AICatalog(key="owners-fixture", name="Owners", kind="jules", adapter="jules")
    session.add_all([p, other, catalog])
    await session.flush()
    tests = [
        ConnectionTest(
            project_id=p.id,
            project_revision=0,
            repository="owner/app",
            connector_id=uuid4(),
            verification={},
            status="completed",
            phase="completed",
            cleanup_status="completed",
            deadline=datetime.now(UTC) + timedelta(hours=1),
        )
        for _ in range(35)
    ]
    session.add_all(tests)
    await session.flush()
    test = tests[0]
    rows = [
        ScheduleConfig(name=name, task_func=task, interval_seconds=60, payload=payload)
        for name, task, payload in [
            ("system", "system.maintain", {}),
            ("dispatch", "pipeline.dispatch_project", {"project_id": str(p.id)}),
            ("observe", "pipeline.observe_project", {"project_id": p.id.hex.upper()}),
            ("legacy-test", "pipeline.connection_test", {"test_id": test.id.hex}),
            ("agent", "jules.session", {"project_id": str(other.id)}),
            ("operator", "jules.session", {"project_id": str(p.id)}),
            ("sync", "jules.sync_sessions", {}),
            ("other", "pipeline.dispatch_project", {"project_id": str(other.id)}),
            ("malformed", "pipeline.dispatch_project", {"project_id": {"bad": str(p.id)}}),
            ("dangling", "pipeline.observe_project", {"project_id": str(uuid4())}),
            ("bad-test", "pipeline.connection_test", {"test_id": [str(test.id)]}),
        ]
    ]
    session.add_all(rows)
    await session.flush()
    agent = ProjectAgentSchedule(
        project_id=p.id,
        schedule_config_id=rows[4].id,
        ai_catalog_id=catalog.id,
        work_type="report",
        title="Owner",
        prompt="Report",
        interval_seconds=60,
    )
    session.add(agent)
    await session.commit()
    return p, other, rows, test, agent


async def test_owner_precedence_detail_and_project_filter(client, session):
    p, _other, _rows, test, agent = await seed(session)
    response = await client.get("/api/v1/schedule_configs", params={"limit": 50, "order_by": "name"})
    assert response.status_code == 200, response.text
    by_name = {r["name"]: r for r in response.json()["items"]}
    expected = {
        "system": ("system_maintenance", False),
        "dispatch": ("project_dispatch", False),
        "observe": ("project_observation", True),
        "legacy-test": ("connection_test", False),
        "agent": ("project_agent_schedule", False),
        "operator": ("operator", True),
        "sync": ("operator", True),
    }
    for name, (kind, allowed) in expected.items():
        row = by_name[name]
        assert row["owner"]["kind"] == kind and row["generic_mutation_allowed"] is allowed
        detail = await client.get(f"/api/v1/schedule_configs/{row['id']}")
        assert detail.json()["owner"] == row["owner"]
    assert by_name["agent"]["owner"] == {
        "kind": "project_agent_schedule",
        "project_id": str(p.id),
        "object_id": str(agent.id),
    }
    assert by_name["legacy-test"]["owner"]["object_id"] == str(test.id)
    for name in ["malformed", "dangling", "bad-test"]:
        assert by_name[name]["owner"]["project_id"] is None
    selected = await client.get(
        "/api/v1/schedule_configs", params={"project_id": str(p.id), "limit": 2, "order_by": "name"}
    )
    assert selected.status_code == 200, selected.text
    assert selected.json()["total_count"] == 4
    page2 = await client.get(
        "/api/v1/schedule_configs", params={"project_id": str(p.id), "limit": 2, "offset": 2, "order_by": "name"}
    )
    assert {r["name"] for r in selected.json()["items"] + page2.json()["items"]} == {
        "agent",
        "dispatch",
        "observe",
        "legacy-test",
    }
    narrowed = await client.get(
        "/api/v1/schedule_configs",
        params={"project_id": str(p.id), "search": "OBSERVE", "enabled": True, "task_func": "pipeline."},
    )
    assert narrowed.json()["total_count"] == 1 and narrowed.json()["items"][0]["name"] == "observe"
    assert (await client.get("/api/v1/schedule_configs", params={"project_id": str(uuid4())})).json()[
        "total_count"
    ] == 0
    assert (await client.get("/api/v1/schedule_configs", params={"project_id": "bad"})).status_code == 422
    for name in ["system", "dispatch", "legacy-test", "agent", "malformed", "bad-test"]:
        assert (
            await client.patch(f"/api/v1/schedule_configs/{by_name[name]['id']}", json={"enabled": False})
        ).status_code == 409
    assert (
        await client.patch(f"/api/v1/schedule_configs/{by_name['observe']['id']}", json={"enabled": False})
    ).status_code == 200


async def test_successful_mutation_reads_are_projected(client):
    data = {"name": "Created operator", "task_func": "jules.session", "interval_seconds": 60}
    response = await client.post("/api/v1/schedule_configs", json=data)
    assert response.status_code == 201, response.text
    row = response.json()
    url = f"/api/v1/schedule_configs/{row['id']}"
    for result in [
        row,
        (await client.patch(url, json={"name": "Renamed"})).json(),
        (await client.put(url, json=data)).json(),
    ]:
        assert result["owner"] == {"kind": "operator", "project_id": None, "object_id": None}
        assert result["generic_mutation_allowed"] is True


@pytest.mark.parametrize(
    "search", ["", "system", "dispatch", "legacy-test", "agent", "observe", "operator", "malformed"]
)
@pytest.mark.parametrize("size", [1, 50])
@pytest.mark.parametrize("skip_count", [False, True])
async def test_page_query_and_checkout_budget(client, session, size, skip_count, search):
    p, _, _rows, _, _ = await seed(session)
    session.add_all(
        [
            ScheduleConfig(
                name=f"zbudget-{i:02}",
                task_func="pipeline.observe_project",
                payload={"project_id": str(p.id)},
                interval_seconds=60,
            )
            for i in range(50)
        ]
    )
    await session.commit()
    counts = {"sql": 0, "checkout": 0}

    def statement(*args):
        counts["sql"] += 1

    def checkout(*args):
        counts["checkout"] += 1

    event.listen(Engine, "before_cursor_execute", statement)
    event.listen(Engine, "checkout", checkout)
    try:
        response = await client.get(
            "/api/v1/schedule_configs",
            params={"limit": size, "skip_count": skip_count, "order_by": "name", "search": search},
        )
    finally:
        event.remove(Engine, "before_cursor_execute", statement)
        event.remove(Engine, "checkout", checkout)
    assert response.status_code == 200, response.text
    expected = 3 if search == "dispatch" else 52 if search == "observe" else 1 if search else 61
    assert len(response.json()["items"]) == min(size, expected)
    assert counts["checkout"] <= 1 and counts["sql"] <= (4 if skip_count else 5), counts
    assert (response.json()["total_count"] is None) is skip_count


async def test_manual_only_persisted_rows_keep_public_read_metadata(client, session):
    _p, _, rows, _, _ = await seed(session)
    operator = next(row for row in rows if row.name == "operator")
    operator.cron_expression = operator.interval_seconds = None
    await session.commit()
    url = f"/api/v1/schedule_configs/{operator.id}"
    detail = await client.get(url)
    assert detail.status_code == 200, detail.text
    listing = await client.get("/api/v1/schedule_configs", params={"search": "operator"})
    assert listing.status_code == 200
    mutation = await client.patch(url, json={"name": "Manual renamed"})
    assert mutation.status_code == 200, mutation.text
    for row in [detail.json(), listing.json()["items"][0], mutation.json()]:
        assert row["cron_expression"] is None and row["interval_seconds"] is None
        assert row["owner"]["kind"] == "operator" and row["generic_mutation_allowed"] is True


async def test_reserved_and_agent_precedence_filter_agree(client, session):
    p, other, rows, _test, agent = await seed(session)
    dispatch = next(row for row in rows if row.name == "dispatch")
    catalog_id = agent.ai_catalog_id
    session.add(
        ProjectAgentSchedule(
            project_id=other.id,
            schedule_config_id=dispatch.id,
            ai_catalog_id=catalog_id,
            work_type="report",
            title="Conflicting retained relation",
            prompt="Inspect",
            interval_seconds=60,
        )
    )
    agent_config = next(row for row in rows if row.name == "agent")
    agent_config.task_func = "pipeline.observe_project"
    await session.commit()
    first = (await client.get("/api/v1/schedule_configs", params={"project_id": str(p.id)})).json()["items"]
    second = (await client.get("/api/v1/schedule_configs", params={"project_id": str(other.id)})).json()["items"]
    by_name = {r["name"]: r for r in first}
    assert by_name["dispatch"]["owner"]["kind"] == "project_dispatch"
    assert by_name["agent"]["owner"]["kind"] == "project_agent_schedule"
    assert by_name["agent"]["owner"]["project_id"] == str(p.id)
    assert "dispatch" not in {r["name"] for r in second}
    assert "agent" not in {r["name"] for r in second}
