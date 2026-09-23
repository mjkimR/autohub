"""Project agent schedules: operator intent in one row, the owned scheduler entry derived from it."""

from uuid import UUID, uuid4

import pytest
from app.features.ai_catalogs.models import AICatalog, AICatalogKind, AICatalogSession, AICatalogState

# Every table the schema under test references must be mapped before the test database is created.
from app.features.configuration.connectors.models import Connector  # noqa: F401
from app.features.project_management.agent_schedules.models import ProjectAgentSchedule
from app.features.project_management.pipeline_runs.models import PipelineRun  # noqa: F401
from app.features.project_management.projects.models import Project  # noqa: F401
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from sqlalchemy import select

from tests.utils.assertions import assert_status_code

pytestmark = pytest.mark.integration
VERIFICATION = {"workflow": "ci.yml", "required_jobs": ["lint"], "event": "pull_request"}


async def add_catalog(session, key: str, kind: str, adapter: str, *, enabled: bool = True) -> str:
    catalog = AICatalog(
        key=key,
        name=key,
        kind=kind,
        adapter=adapter,
        enabled=enabled,
        availability_state=AICatalogState.NORMAL,
        revision=1,
    )
    session.add(catalog)
    await session.flush()
    catalog_id = str(catalog.id)
    await session.commit()
    return catalog_id


@pytest.fixture
async def jules(client, session) -> str:
    return await add_catalog(session, "personal-jules", AICatalogKind.JULES, "jules-api")


@pytest.fixture
async def codex(client, session) -> str:
    return await add_catalog(session, "personal-codex", AICatalogKind.CODEX, "codex-github-mention")


@pytest.fixture
async def project(client) -> dict:
    connector = await client.post(
        "/api/v1/connectors",
        json={"name": "github-account", "provider": "github", "credentials": {"token": "github-test-token"}},
    )
    assert_status_code(connector, 201)
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Application",
            "repository": "owner/app",
            "github_connector_id": connector.json()["id"],
            "verification": VERIFICATION,
        },
    )
    assert_status_code(response, 201)
    return response.json()


def payload(catalog_id: str, **overrides) -> dict:
    return {
        "ai_catalog_id": catalog_id,
        "work_type": "report",
        "title": "Weekly hygiene report",
        "prompt": "Report stale dependencies.",
        "cron_expression": "0 9 * * 1",
        **overrides,
    }


async def configs_by_task(session, task_func: str) -> list[ScheduleConfig]:
    session.expire_all()
    return list((await session.scalars(select(ScheduleConfig).where(ScheduleConfig.task_func == task_func))).all())


async def test_creating_a_schedule_derives_only_its_session_entry(client, session, project, jules):
    response = await client.post(f"/api/v1/projects/{project['id']}/agent-schedules", json=payload(jules))

    assert_status_code(response, 201)
    created = response.json()
    assert (created["work_type"], created["task_func"], created["enabled"]) == ("report", "jules.session", True)
    assert created["next_run_at"] is not None and created["recent_sessions"] == []

    [config] = await configs_by_task(session, "jules.session")
    assert str(config.id) == created["schedule_config_id"]
    assert config.payload == {
        "catalog_key": "personal-jules",
        "repository": "owner/app",
        "starting_branch": "main",
        "title": "Weekly hygiene report",
        "prompt": "Report stale dependencies.",
        "work_type": "report",
    }
    assert (config.cron_expression, config.enabled) == ("0 9 * * 1", True)
    assert "Application" in config.name
    assert await configs_by_task(session, "jules.sync_sessions") == []

    listing = await client.get(f"/api/v1/projects/{project['id']}/agent-schedules")
    assert_status_code(listing, 200)
    assert [item["id"] for item in listing.json()["items"]] == [created["id"]]


async def test_updating_rewrites_the_entry_and_a_trigger_change_recomputes_the_next_run(
    client, session, project, jules
):
    root = f"/api/v1/projects/{project['id']}/agent-schedules"
    created = (await client.post(root, json=payload(jules))).json()
    first_next = created["next_run_at"]

    unchanged = await client.put(f"{root}/{created['id']}", json=payload(jules, title="Weekly report v2"))
    assert_status_code(unchanged, 200)
    assert unchanged.json()["next_run_at"] == first_next
    [config] = await configs_by_task(session, "jules.session")
    assert config.payload["title"] == "Weekly report v2"

    retimed = await client.put(
        f"{root}/{created['id']}",
        json=payload(jules, cron_expression=None, interval_seconds=3600, work_type="task", enabled=False),
    )
    assert_status_code(retimed, 200)
    assert retimed.json()["next_run_at"] != first_next
    [config] = await configs_by_task(session, "jules.session")
    assert (config.interval_seconds, config.cron_expression, config.enabled) == (3600, None, False)
    assert config.payload["work_type"] == "task"


async def test_deleting_the_last_schedule_removes_its_entry_and_the_catalog_sync(client, session, project, jules):
    root = f"/api/v1/projects/{project['id']}/agent-schedules"
    first = (await client.post(root, json=payload(jules))).json()
    second = (await client.post(root, json=payload(jules, title="Second"))).json()

    assert_status_code(await client.delete(f"{root}/{first['id']}"), 204)
    assert len(await configs_by_task(session, "jules.session")) == 1
    assert await configs_by_task(session, "jules.sync_sessions") == []

    assert_status_code(await client.delete(f"{root}/{second['id']}"), 204)
    assert await configs_by_task(session, "jules.session") == []
    assert await configs_by_task(session, "jules.sync_sessions") == []
    assert_status_code(await client.get(f"{root}/{second['id']}"), 404)


async def test_run_now_makes_the_entry_due_immediately(client, session, project, jules):
    root = f"/api/v1/projects/{project['id']}/agent-schedules"
    created = (await client.post(root, json=payload(jules))).json()

    response = await client.post(f"{root}/{created['id']}/run-now")

    assert_status_code(response, 200)
    assert response.json()["next_run_at"] is None
    [config] = await configs_by_task(session, "jules.session")
    assert config.next_run_at is None

    disabled = (await client.put(f"{root}/{created['id']}", json=payload(jules, enabled=False))).json()
    assert disabled["enabled"] is False
    assert_status_code(await client.post(f"{root}/{created['id']}/run-now"), 422)


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ({"work_type": "task"}, "cannot run scheduled task sessions"),
        ({"work_type": "report"}, "cannot run scheduled report sessions"),
    ],
)
async def test_a_catalog_without_session_work_is_refused(client, project, codex, body, detail):
    response = await client.post(f"/api/v1/projects/{project['id']}/agent-schedules", json=payload(codex, **body))

    assert_status_code(response, 422)
    assert detail in response.json()["detail"]


async def test_a_disabled_catalog_and_a_bad_trigger_are_refused(client, session, project, jules):
    root = f"/api/v1/projects/{project['id']}/agent-schedules"
    off = await add_catalog(session, "old-jules", AICatalogKind.JULES, "jules-api", enabled=False)

    assert_status_code(await client.post(root, json=payload(off)), 422)
    assert_status_code(await client.post(root, json=payload(jules, cron_expression=None)), 422)
    assert_status_code(await client.post(root, json=payload(jules, interval_seconds=600)), 422)
    assert_status_code(await client.post(root, json=payload(jules, cron_expression="not a cron")), 422)


async def test_a_project_without_a_repository_cannot_schedule_sessions(client, session, jules):
    bare = await client.post("/api/v1/projects", json={"name": "Bare"})
    assert_status_code(bare, 201)

    response = await client.post(f"/api/v1/projects/{bare.json()['id']}/agent-schedules", json=payload(jules))

    assert_status_code(response, 422)
    assert "GitHub repository" in response.json()["detail"]


async def test_project_changes_flow_into_owned_entries(client, session, project, jules):
    root = f"/api/v1/projects/{project['id']}/agent-schedules"
    await client.post(root, json=payload(jules))

    renamed = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={
            "name": "Renamed",
            "enabled": False,
            "expected_revision": project["revision"],
            "github": {**project["github"], "repository": "owner/other"},
        },
    )
    assert_status_code(renamed, 200)

    [config] = await configs_by_task(session, "jules.session")
    assert config.payload["repository"] == "owner/other"
    assert "Renamed" in config.name
    # A disabled project pauses its agent schedules without touching their own switch.
    assert config.enabled is False
    listing = (await client.get(root)).json()["items"]
    assert listing[0]["enabled"] is True


async def test_re_enabling_a_schedule_recomputes_its_next_run(client, session, project, jules):
    root = f"/api/v1/projects/{project['id']}/agent-schedules"
    created = (await client.post(root, json=payload(jules, enabled=False))).json()
    [config] = await configs_by_task(session, "jules.session")
    # A stale due time left over from before the pause must not fire the moment the schedule turns on.
    config.next_run_at = None
    await session.commit()

    enabled = await client.put(f"{root}/{created['id']}", json=payload(jules, enabled=True))

    assert_status_code(enabled, 200)
    assert enabled.json()["next_run_at"] is not None


async def test_disabling_the_catalog_pauses_its_agent_schedules(client, session, project, jules):
    root = f"/api/v1/projects/{project['id']}/agent-schedules"
    created = (await client.post(root, json=payload(jules))).json()

    disabled = await client.put("/api/v1/ai-catalogs/personal-jules/enabled", json={"enabled": False})
    assert_status_code(disabled, 200)
    [config] = await configs_by_task(session, "jules.session")
    assert config.enabled is False
    assert (await client.get(root)).json()["items"][0]["enabled"] is True
    refused = await client.post(f"{root}/{created['id']}/run-now")
    assert_status_code(refused, 422)
    # The schedule stays editable while its catalog is off; its entry simply stays paused.
    renamed = await client.put(f"{root}/{created['id']}", json=payload(jules, title="Renamed while paused"))
    assert_status_code(renamed, 200)
    [config] = await configs_by_task(session, "jules.session")
    assert (config.enabled, config.payload["title"]) == (False, "Renamed while paused")
    config.next_run_at = None
    await session.commit()

    enabled = await client.put("/api/v1/ai-catalogs/personal-jules/enabled", json={"enabled": True})
    assert_status_code(enabled, 200)
    [config] = await configs_by_task(session, "jules.session")
    assert config.enabled is True and config.next_run_at is not None


async def test_an_operator_sync_entry_for_the_catalog_is_left_alone(client, session, project, jules):
    session.add(
        ScheduleConfig(
            name="My own jules sync",
            task_func="jules.sync_sessions",
            interval_seconds=600,
            payload={"catalog_key": "personal-jules"},
            enabled=False,
        )
    )
    await session.commit()
    root = f"/api/v1/projects/{project['id']}/agent-schedules"

    created = (await client.post(root, json=payload(jules))).json()
    names = sorted(config.name for config in await configs_by_task(session, "jules.sync_sessions"))
    assert names == ["My own jules sync"]

    assert_status_code(await client.delete(f"{root}/{created['id']}"), 204)
    names = [config.name for config in await configs_by_task(session, "jules.sync_sessions")]
    assert names == ["My own jules sync"]


async def test_disconnecting_the_project_from_github_pauses_its_agent_schedules(client, session, project, jules):
    await client.post(f"/api/v1/projects/{project['id']}/agent-schedules", json=payload(jules))

    disconnected = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"name": project["name"], "enabled": True, "expected_revision": project["revision"], "github": None},
    )
    assert_status_code(disconnected, 200)

    [config] = await configs_by_task(session, "jules.session")
    assert config.enabled is False and config.payload["repository"] is None


async def test_the_generic_schedule_api_refuses_to_touch_an_owned_entry(client, session, project, jules):
    created = (await client.post(f"/api/v1/projects/{project['id']}/agent-schedules", json=payload(jules))).json()
    config_id = created["schedule_config_id"]

    patched = await client.patch(f"/api/v1/schedule_configs/{config_id}", json={"enabled": False})
    assert_status_code(patched, 409)
    assert "managed by a project agent schedule" in patched.json()["detail"]
    assert_status_code(await client.delete(f"/api/v1/schedule_configs/{config_id}"), 409)
    # Reading stays open so the generic screen can still show the entry.
    assert_status_code(await client.get(f"/api/v1/schedule_configs/{config_id}"), 200)


async def test_deleting_a_project_removes_its_agent_schedules(client, session, project, jules):
    await client.post(f"/api/v1/projects/{project['id']}/agent-schedules", json=payload(jules))

    assert_status_code(await client.delete(f"/api/v1/projects/{project['id']}"), 204)

    session.expire_all()
    assert (await session.scalars(select(ProjectAgentSchedule))).all() == []
    assert await configs_by_task(session, "jules.session") == []
    assert await configs_by_task(session, "jules.sync_sessions") == []


async def test_recent_sessions_started_by_the_schedule_are_listed(client, session, project, jules):
    created = (await client.post(f"/api/v1/projects/{project['id']}/agent-schedules", json=payload(jules))).json()
    for index in range(7):
        session.add(
            AICatalogSession(
                id=uuid4(),
                ai_catalog_id=UUID(jules),
                schedule_config_id=UUID(created["schedule_config_id"]),
                title=f"Run {index}",
                work_type="report",
                state="completed",
                result_summary=f"Report {index}",
            )
        )
    await session.commit()

    response = await client.get(f"/api/v1/projects/{project['id']}/agent-schedules/{created['id']}")

    assert_status_code(response, 200)
    recent = response.json()["recent_sessions"]
    assert len(recent) == 5
    assert all(item["result_summary"].startswith("Report") for item in recent)


async def test_api_created_jules_catalog_can_own_an_agent_schedule(client, session, project):
    key = await client.post(
        "/api/v1/connectors",
        json={"name": "Extra Jules key", "provider": "jules", "credentials": {"token": "test-jules-key"}},
    )
    assert_status_code(key, 201)
    catalog = await client.post(
        "/api/v1/ai-catalogs",
        json={
            "key": "extra-jules",
            "name": "Extra Jules",
            "kind": "jules",
            "connector_id": key.json()["id"],
            "configured_concurrency": 2,
            "policy_config": {"daily_task_limit": 5},
        },
    )
    assert_status_code(catalog, 201)
    schedule = await client.post(
        f"/api/v1/projects/{project['id']}/agent-schedules", json=payload(catalog.json()["id"])
    )
    assert_status_code(schedule, 201)
    [config] = await configs_by_task(session, "jules.session")
    assert config.payload["catalog_key"] == "extra-jules"
    assert await configs_by_task(session, "jules.sync_sessions") == []
    assert (await client.get("/api/v1/ai-catalogs/extra-jules/sessions")).json()["items"] == []
