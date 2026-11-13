from uuid import UUID, uuid4

import pytest
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.sdd.batch_models import SddActivityClaim, SddBatch

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

project = scenarios.project
github = scenarios.github
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "runtime"),
        ("post", "readiness"),
        ("get", "milestones"),
        ("post", "milestone-preview"),
        ("post", "batches"),
    ],
)
async def test_retired_evaluation_routes_refuse_before_external_reads(client, project, github, method, path):
    github.paths.clear()
    response = await getattr(client, method)(f"/api/v1/projects/{project['id']}/sdd/{path}")
    assert response.status_code == 410, response.text
    assert response.json()["code"] == "SDD_EXECUTION_RETIRED"
    assert github.paths == []


async def test_retained_batch_reads_and_local_stop_never_resume_execution(client, project, session, github):
    row = SddBatch(
        project_id=UUID(project["id"]),
        request_id=uuid4(),
        request_digest="0" * 64,
        actor="operator",
        basis={"sha": "a" * 40},
        evaluation={},
        state="running",
    )
    session.add(row)
    await session.commit()
    root = f"/api/v1/projects/{project['id']}/sdd/batches"
    github.paths.clear()
    assert (await client.get(root)).json()[0]["id"] == str(row.id)
    detail = await client.get(f"{root}/{row.id}")
    assert detail.json()["retired"] is True and detail.json()["basis"]["sha"] == "a" * 40
    request = {"request_id": str(uuid4()), "expected_revision": row.revision, "action": "resume"}
    response = await client.post(f"{root}/{row.id}/controls", json=request)
    assert response.status_code == 410
    request["action"] = "stop"
    response = await client.post(f"{root}/{row.id}/controls", json=request)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "stopped" and not response.json()["exclusion"]
    repeated = await client.post(f"{root}/{row.id}/controls", json=request)
    assert repeated.json() == response.json()
    assert github.paths == []


async def retired_claim(session, project):
    row = SddActivityClaim(
        project_id=UUID(project["id"]),
        request_id=uuid4(),
        actor="operator",
        request_digest="0" * 64,
        unit="docs/proposals/PROP-demo",
        activity="dev",
        checkpoint={"retired": True, "uncertain": True, "branch": "dev-demo", "pull_number": 7},
    )
    session.add(row)
    await session.commit()
    return row


async def test_claim_acknowledgment_requires_exact_evidence_and_is_idempotent(client, project, session, github):
    row = await retired_claim(session, project)
    root = f"/api/v1/projects/{project['id']}/sdd/claims/{row.id}"
    evidence = (await client.get(root)).json()
    assert evidence["retired"] and not evidence["settled"]
    request = {"request_id": str(uuid4()), "expected_checkpoint_digest": "f" * 64, "acknowledge_external_work": True}
    assert (await client.post(root + "/reconcile", json=request)).status_code == 409
    request["expected_checkpoint_digest"] = evidence["checkpoint_digest"]
    github.paths.clear()
    response = await client.post(root + "/reconcile", json=request)
    assert response.status_code == 200, response.text
    assert (
        response.json()["settled"]
        and response.json()["checkpoint"]["reconciliation"]["request_id"] == request["request_id"]
    )
    assert (await client.post(root + "/reconcile", json=request)).json() == response.json()
    assert github.paths == []


async def test_direct_retired_run_acknowledgment_never_resumes(client, project, github, session):
    response = await scenarios.enroll(client, project)
    assert response.status_code == 201, response.text
    run = await session.get(PipelineRun, UUID(response.json()["id"]))
    run.state = "canceled"
    run.sdd_snapshot = {"provider": "devkit-spec", "spec_dir": "docs/proposals/PROP-demo"}
    run.sdd_progress = {"retirement": {"external_work_unreconciled": True}}
    run.lease_owner = run.lease_token = run.lease_expires_at = None
    await session.commit()
    body = {"request_id": str(uuid4()), "expected_revision": run.revision, "acknowledge_external_work": True}
    path = f"/api/v1/projects/{project['id']}/sdd/runs/{run.id}/reconcile"
    github.paths.clear()
    response = await client.post(path, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "canceled"
    assert not response.json()["sdd_progress"]["retirement"]["external_work_unreconciled"]
    assert (await client.post(path, json=body)).json() == response.json()
    assert github.paths == []


async def test_claim_reconciliation_acknowledges_exact_linked_retired_run(client, project, github, session):
    enrolled = await scenarios.enroll(client, project)
    run = await session.get(PipelineRun, UUID(enrolled.json()["id"]))
    run.state = "canceled"
    run.sdd_snapshot = {"provider": "devkit-spec", "spec_dir": "docs/proposals/PROP-demo"}
    run.sdd_progress = {"retirement": {"external_work_unreconciled": True}}
    await session.commit()
    claim = await retired_claim(session, project)
    claim.run_id = run.id
    await session.commit()
    root = f"/api/v1/projects/{project['id']}/sdd/claims/{claim.id}"
    retained = (await client.get(root)).json()
    response = await client.post(
        root + "/reconcile",
        json={
            "request_id": str(uuid4()),
            "expected_checkpoint_digest": retained["checkpoint_digest"],
            "acknowledge_external_work": True,
        },
    )
    assert response.status_code == 200, response.text
    current = (await client.get(f"/api/v1/pipeline-runs/{run.id}")).json()
    assert current["state"] == "canceled" and response.json()["settled"]
    assert not current["sdd_progress"]["retirement"]["external_work_unreconciled"]


async def test_legacy_claim_replay_is_retired_and_different_request_keeps_owner(client, project, session):
    from unittest.mock import AsyncMock

    from app.features.project_management.projects.errors import ProjectError
    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.schemas import StartActivityRequest

    claim = await retired_claim(session, project)
    projects = ProjectService(ProjectRepository())
    owner = await projects.get(session, UUID(project["id"]))
    claims = ActivityClaims(projects, AsyncMock(), AsyncMock())
    with pytest.raises(ProjectError) as error:
        await claims.reserve(
            session, owner, "dev", "demo", StartActivityRequest(request_id=claim.request_id), "operator"
        )
    assert error.value.status == 410 and error.value.code == "SDD_EXECUTION_RETIRED"
    with pytest.raises(ProjectError) as error:
        await claims.reserve(session, owner, "dev", "demo", StartActivityRequest(request_id=uuid4()), "operator")
    assert error.value.status == 409 and str(claim.id) in error.value.detail
    with pytest.raises(ProjectError) as error:
        await claims.execute(owner.id, claim.id)
    assert error.value.status == 410


@pytest.mark.parametrize("where", ["checkpoint", "settlement"])
async def test_expired_activity_worker_cannot_mutate_or_settle_claim(project, session, monkeypatch, where):
    from datetime import timedelta
    from unittest.mock import AsyncMock

    from app.features.project_management.projects.errors import ProjectError
    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd import activities
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.schemas import StartActivityRequest
    from app_layer_base.core.database.transaction import AsyncTransaction
    from app_testing_base import utc_now

    projects = ProjectService(ProjectRepository())
    claims = ActivityClaims(projects, AsyncMock(), AsyncMock())
    owner = await projects.get(session, UUID(project["id"]))
    claim = await claims.reserve(session, owner, "dev", "demo", StartActivityRequest(request_id=uuid4()), "operator")
    claim_id = claim.id
    await session.commit()

    async def expired(*args, checkpoint, **kwargs):
        async with AsyncTransaction() as tx:
            row = await tx.get(SddActivityClaim, claim_id)
            assert row is not None
            row.checkpoint = {**row.checkpoint, "lease_expires_at": (utc_now() - timedelta(seconds=1)).isoformat()}
        if where == "checkpoint":
            await checkpoint(initial_sha="b" * 40)
        return type("Result", (), {"id": uuid4()})()

    monkeypatch.setattr(activities.ActivityStarter, "start", expired)
    with pytest.raises(ProjectError, match=r"fence|reconciliation"):
        await claims.execute(owner.id, claim_id)
    await session.refresh(claim)
    assert claim.run_id is None and not claim.settled
    assert "initial_sha" not in claim.checkpoint and "refusal" not in claim.checkpoint


async def test_postgres_concurrent_activity_requests_keep_one_publication_owner(project, session):
    import asyncio
    from unittest.mock import AsyncMock

    from app.features.project_management.projects.errors import ProjectError
    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.schemas import StartActivityRequest
    from app_layer_base.core.database.transaction import AsyncTransaction

    if session.get_bind().dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock race")
    await session.commit()
    projects = ProjectService(ProjectRepository())
    claims = ActivityClaims(projects, AsyncMock(), AsyncMock())

    async def reserve():
        async with AsyncTransaction() as tx:
            owner = await projects.get(tx, UUID(project["id"]), lock=True)
            row = await claims.reserve(tx, owner, "plan", "race", StartActivityRequest(request_id=uuid4()), "operator")
            return row.id

    results = await asyncio.gather(reserve(), reserve(), return_exceptions=True)
    assert sum(isinstance(result, UUID) for result in results) == 1
    conflicts = [result for result in results if isinstance(result, ProjectError)]
    assert len(conflicts) == 1 and conflicts[0].status == 409


@pytest.mark.parametrize("expiry", [None, "expired"])
async def test_uncertain_optimistic_publication_can_be_explicitly_settled_without_replacement(
    client,
    project,
    session,
    github,
    expiry,
):
    from datetime import timedelta

    from app_testing_base import utc_now

    claim = await retired_claim(session, project)
    candidate = {
        "execution_version": 2,
        "uncertain": True,
        "pr_attempted": True,
        "initial_sha": "b" * 40,
        "branch": "dev-demo",
        "ref_attempted": True,
        "lease_expires_at": (utc_now() - timedelta(seconds=1)).isoformat() if expiry else None,
    }
    claim.checkpoint = candidate
    await session.commit()
    root = f"/api/v1/projects/{project['id']}/sdd/claims/{claim.id}"
    evidence = (await client.get(root)).json()
    assert not evidence["retired"] and not evidence["settled"]
    body = {
        "request_id": str(uuid4()),
        "expected_checkpoint_digest": evidence["checkpoint_digest"],
        "acknowledge_external_work": True,
    }
    github.paths.clear()
    response = await client.post(root + "/reconcile", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["settled"] and response.json()["retired"]
    assert response.json()["checkpoint"]["initial_sha"] == candidate["initial_sha"]
    assert response.json()["checkpoint"]["branch"] == candidate["branch"]
    assert response.json()["run_id"] is None
    assert (await client.post(root + "/reconcile", json=body)).json() == response.json()
    assert github.paths == []


@pytest.mark.parametrize("reason", ["live-lease", "known-outcome", "run-owner"])
async def test_optimistic_settlement_refuses_current_authority(client, project, session, github, reason):
    from datetime import timedelta

    from app_testing_base import utc_now

    claim = await retired_claim(session, project)
    checkpoint = {"execution_version": 2, "uncertain": reason != "known-outcome"}
    if reason == "live-lease":
        checkpoint.update(
            lease="private-lease-capability", lease_expires_at=(utc_now() + timedelta(minutes=5)).isoformat()
        )
    claim.checkpoint = checkpoint
    await session.commit()
    if reason == "run-owner":
        enrolled = await scenarios.enroll(client, project)
        assert enrolled.status_code == 201, enrolled.text
        claim.run_id = UUID(enrolled.json()["id"])
    claim.checkpoint = checkpoint
    await session.commit()
    root = f"/api/v1/projects/{project['id']}/sdd/claims/{claim.id}"
    evidence = (await client.get(root)).json()
    assert "lease" not in evidence["checkpoint"]
    body = {
        "request_id": str(uuid4()),
        "expected_checkpoint_digest": evidence["checkpoint_digest"],
        "acknowledge_external_work": True,
    }
    github.paths.clear()
    response = await client.post(root + "/reconcile", json=body)
    assert response.status_code == 409, response.text
    await session.refresh(claim)
    assert not claim.settled and "reconciliation" not in claim.checkpoint
    assert github.paths == []
