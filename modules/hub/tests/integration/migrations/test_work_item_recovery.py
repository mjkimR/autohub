from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from tests.integration.features.project_management.work_plans.conftest import setup_work
from tests.integration.features.project_management.work_plans.test_work_plans import create, spec
from tests.integration.migrations.test_default_ai_catalogs import scripts

__all__ = ["setup_work"]
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_additive_recovery_migration_preserves_legacy_rows(client, setup_work, session):
    project, _, _, _ = setup_work
    plan = await create(client, project, spec(state="paused"))
    connection = await session.connection()

    def roundtrip(conn):
        migration = scripts().get_revision("c03d206a98ad").module
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            assert "work_item_recoveries" not in inspect(conn).get_table_names()
            assert conn.scalar(text("SELECT count(*) FROM work_items")) == 2
            conn.execute(text("UPDATE work_items SET state = CASE WHEN key = 'a' THEN 'preparation_failed' ELSE 'succeeded' END"))
            migration.upgrade()
        assert [r[0] for r in conn.execute(text("SELECT state FROM work_items ORDER BY key"))] == ["preparation_failed", "succeeded"]
        assert conn.scalar(text("SELECT count(*) FROM work_item_recoveries")) == 0
        assert conn.scalar(text("SELECT count(*) FROM work_item_recovery_events")) == 0
        assert conn.scalar(text("SELECT count(*) FROM work_items")) == 2
        indexes = {i["name"] for i in inspect(conn).get_indexes("work_item_recoveries")}
        assert "uq_work_item_pending_recovery" in indexes
        assert any(
            c["name"] == "uq_work_item_recovery_request"
            for c in inspect(conn).get_unique_constraints("work_item_recoveries")
        )
        assert scripts().get_heads() == ["c03d206a98ad"]

    await connection.run_sync(roundtrip)
    await session.commit()

    await session.execute(text("UPDATE work_plans SET state='active'"))
    await session.commit()
    response = await client.post(f"/api/v1/projects/{project['id']}/work-plans/{plan['id']}/items/{plan['items'][0]['id']}/recover",
        json={"request_id": str(uuid4()), "expected_revision": 1, "reason": "Verify migrated persistence"})
    assert response.status_code == 200, response.text
    assert response.json()["recovery"]["created_at"]
    assert response.json()["recovery"]["events"][0]["kind"] == "accepted"
