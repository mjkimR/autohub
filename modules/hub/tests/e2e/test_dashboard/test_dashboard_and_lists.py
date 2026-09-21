from datetime import timedelta

import pytest
from app.features.ai_catalogs.models import AICatalog
from app.features.configuration.connectors.models import Connector
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.projects.models import Project
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from app_testing_base import utc_now

pytestmark = [pytest.mark.e2e, pytest.mark.real_commit]


@pytest.fixture
async def history(session):
    projects = [Project(name=f"hygiene-project-{i:03d}", enabled=True) for i in range(51)]
    catalog = AICatalog(key="hygiene-catalog", name="Review", kind="codex", adapter="codex-github-mention")
    session.add_all([*projects, catalog])
    await session.flush()
    now = utc_now()
    runs = []
    for i in range(51):
        number = i + 1
        snapshot = {
            "number": number,
            "url": f"https://github.com/owner/app/pull/{number}",
            "title": "Unique 100% fix" if number == 51 else f"Implement feature {number}",
            "base_ref": "main",
            "head_ref": f"feature/{number}",
            "head_sha": "a" * 40,
        }
        runs.append(
            PipelineRun(
                project_id=projects[-1].id,
                ai_catalog_id=catalog.id,
                project_revision=1,
                pull_number=number,
                pull_url=snapshot["url"],
                pull_snapshot=snapshot,
                branch=snapshot["head_ref"],
                state="blocked" if number == 51 else "completed",
                created_at=now - timedelta(minutes=i),
            )
        )
    session.add_all(runs)
    await session.commit()
    return projects, runs


async def test_dashboard_counts_history_and_connectors_beyond_the_first_page(client, session, history):
    baseline = (await client.get("/api/v1/dashboard/stats")).json()
    session.add_all(
        [
            Connector(
                name=f"hygiene-connector-{i:03d}",
                provider="github",
                enabled=i < 101,
                credentials_ciphertext=b"test",
                credentials_nonce=b"nonce",
                credential_key_version="test",
            )
            for i in range(102)
        ]
    )
    session.add_all(
        [ScheduleConfig(name=f"hygiene-schedule-{i}", task_func="test.task", interval_seconds=60) for i in range(101)]
    )
    await session.commit()

    response = await client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs"] == 51
    assert data["runs_by_state"]["completed"] == 50
    assert data["runs_by_state"]["blocked"] == 1
    assert sum(data["runs_by_state"].values()) == data["total_runs"]
    assert data["project_count"] == 51
    assert data["connector_count"] == baseline["connector_count"] + 102
    assert data["active_connector_count"] == baseline["active_connector_count"] + 101
    assert data["schedule_count"] == baseline["schedule_count"] + 101


async def test_project_pages_and_search_share_the_same_filter(client, history):
    first = (await client.get("/api/v1/projects", params={"limit": 50})).json()
    last = (await client.get("/api/v1/projects", params={"offset": 50, "limit": 50})).json()
    assert first["total_count"] == last["total_count"] == 51
    assert len(first["items"]) == 50
    assert [p["name"] for p in last["items"]] == ["hygiene-project-050"]
    found = (await client.get("/api/v1/projects", params={"search": "PROJECT-050"})).json()
    assert found["total_count"] == 1
    assert found["items"][0]["id"] == last["items"][0]["id"]
    empty = (await client.get("/api/v1/projects", params={"search": "%"})).json()
    assert empty == {"items": [], "total_count": 0}


async def test_run_filters_search_before_pagination_and_treat_wildcards_literally(client, history):
    projects, _ = history
    first = (await client.get("/api/v1/pipeline-runs", params={"limit": 50})).json()
    last = (await client.get("/api/v1/pipeline-runs", params={"offset": 50})).json()
    assert len(first["items"]) == 50 and first["total_count"] == 51
    assert [r["pull_number"] for r in last["items"]] == [51]
    for search in ["UNIQUE", "PR #51", "feature/51", "%"]:
        response = await client.get(
            "/api/v1/pipeline-runs",
            params={
                "search": search,
                "state": "blocked",
                "project_id": str(projects[-1].id),
            },
        )
        assert response.status_code == 200
        assert response.json()["total_count"] == 1
        assert response.json()["items"][0]["pull_number"] == 51
    response = await client.get("/api/v1/pipeline-runs", params={"state": "blocked", "project_id": str(projects[0].id)})
    assert response.json() == {"items": [], "total_count": 0}
    assert (await client.get("/api/v1/pipeline-runs", params={"state": "unknown"})).status_code == 422


async def test_empty_dashboard_has_zero_counters(client):
    data = (await client.get("/api/v1/dashboard/stats")).json()
    assert data["total_runs"] == data["project_count"] == 0
    assert all(value == 0 for value in data["runs_by_state"].values())
