from datetime import UTC, datetime, timedelta

import pytest
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from app.features.scheduling.schedule_jobs.models import ScheduleJob

from tests.utils.assertions import assert_status_code

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.mark.parametrize("kind", ["schedule_configs", "schedule_jobs"])
async def test_search_filters_and_count_cover_rows_beyond_the_first_page(client, session, kind):
    now = datetime(2026, 9, 21, tzinfo=UTC)
    names = [f"Recent {i:02}" for i in range(50)] + ["Literal_%_Report", "Old report"]
    for index, name in enumerate(names):
        timestamp = now - timedelta(minutes=index)
        if kind == "schedule_configs":
            row = ScheduleConfig(
                name=name,
                task_func="tasks.audit" if index < 51 else "tasks.special",
                interval_seconds=300,
                payload={},
                enabled=index < 51,
                created_at=timestamp,
            )
        else:
            row = ScheduleJob(
                name=name, status="success" if index < 51 else "failure", payload={}, started_at=timestamp
            )
        session.add(row)
    await session.commit()
    url = f"/api/v1/{kind}"
    first = await client.get(url, params={"limit": 50, "offset": 0})
    assert_status_code(first, 200)
    assert first.json()["total_count"] == 52
    assert [item["name"] for item in first.json()["items"]] == names[:50]
    second = await client.get(url, params={"limit": 50, "offset": 50})
    assert [item["name"] for item in second.json()["items"]] == names[50:]
    assert {item["id"] for item in first.json()["items"]}.isdisjoint(item["id"] for item in second.json()["items"])

    # Wildcards in user input must match literally, including when surrounded by spaces.
    literal = await client.get(url, params={"search": "  %_  ", "limit": 1})
    assert literal.json()["total_count"] == 1
    assert literal.json()["items"][0]["name"] == "Literal_%_Report"
    filtered = await client.get(url, params={"search": "REPORT", "limit": 1})
    assert filtered.json()["total_count"] == 2
    assert filtered.json()["items"][0]["name"] == "Literal_%_Report"
    next_filtered = await client.get(url, params={"search": "REPORT", "limit": 1, "offset": 1})
    assert next_filtered.json()["total_count"] == 2
    assert next_filtered.json()["items"][0]["name"] == "Old report"

    status = {"enabled": "false"} if kind == "schedule_configs" else {"status": "failure"}
    narrowed = await client.get(url, params={"search": "REPORT", **status})
    assert narrowed.json()["total_count"] == 1
    assert narrowed.json()["items"][0]["name"] == "Old report"
    column = await client.get(url, params={"search": "SPECIAL" if kind == "schedule_configs" else "FAILURE"})
    assert column.json()["total_count"] == 1
    assert column.json()["items"][0]["name"] == "Old report"
    empty = await client.get(url, params={"search": "does-not-exist"})
    assert empty.json()["total_count"] == 0 and empty.json()["items"] == []
    assert_status_code(await client.get(url, params={"search": "x" * 201}), 422)
