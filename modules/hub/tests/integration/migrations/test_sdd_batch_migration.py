import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from tests.integration.migrations.test_default_ai_catalogs import scripts

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_sdd_batch_migration_roundtrip_preserves_projects(session):
    connection = await session.connection()

    def roundtrip(conn):
        before = conn.scalar(text("SELECT count(*) FROM projects"))
        migration = scripts().get_revision("e25f428cba0f").module
        with Operations.context(MigrationContext.configure(conn)):
            cleanup = scripts().get_revision("d704fb51a433").module
            cleanup.downgrade()
            migration.downgrade()
            assert "sdd_batches" not in inspect(conn).get_table_names()
            migration.upgrade()
            cleanup.upgrade()
        tables = inspect(conn).get_table_names()
        assert "sdd_activity_claims" in tables
        assert not {"sdd_batches", "sdd_batch_members", "sdd_batch_controls", "sdk_flow_pr_links"} & set(tables)
        assert "member_id" not in {c["name"] for c in inspect(conn).get_columns("sdd_activity_claims")}
        assert conn.scalar(text("SELECT count(*) FROM projects")) == before
        assert "uq_sdd_activity_claim_live" in {r["name"] for r in inspect(conn).get_indexes("sdd_activity_claims")}
        assert scripts().get_heads() == ["d704fb51a433"]

    await connection.run_sync(roundtrip)
    await session.commit()


async def test_cleanup_preserves_standalone_activity_claims(session):
    from uuid import uuid4

    from app.features.project_management.projects.models import Project
    from app.features.project_management.sdd.claim_models import SddActivityClaim

    project = Project(name="Claim migration")
    session.add(project)
    await session.flush()
    claim = SddActivityClaim(
        project_id=project.id,
        request_id=uuid4(),
        request_digest="a" * 64,
        actor="operator",
        unit="docs/proposals/PROP-current",
        activity="plan",
        checkpoint={"uncertain": True, "branch": "plan-current"},
    )
    session.add(claim)
    await session.flush()
    identity = claim.id
    await session.commit()
    connection = await session.connection()

    def cleanup(conn):
        migration = scripts().get_revision("d704fb51a433").module
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            assert "member_id" in {c["name"] for c in inspect(conn).get_columns("sdd_activity_claims")}
            migration.upgrade()
        assert conn.scalar(text("SELECT count(*) FROM sdd_activity_claims")) == 1
        assert "member_id" not in {c["name"] for c in inspect(conn).get_columns("sdd_activity_claims")}
        assert "uq_sdd_activity_claim_live" in {i["name"] for i in inspect(conn).get_indexes("sdd_activity_claims")}

    await connection.run_sync(cleanup)
    await session.commit()
    await session.refresh(claim)
    assert claim.id == identity and not claim.settled
    assert claim.checkpoint == {"uncertain": True, "branch": "plan-current"}
