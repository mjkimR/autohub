from uuid import UUID, uuid4

import pytest
from app.features.project_management.sdd.claim_models import SddActivityClaim

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

project = scenarios.project
github = scenarios.github
mention_github = scenarios.mention_github
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
async def test_removed_native_routes_have_no_external_effects(client, project, github, method, path):
    github.paths.clear()
    response = await getattr(client, method)(f"/api/v1/projects/{project['id']}/sdd/{path}")
    assert response.status_code == 404, response.text
    assert github.paths == []


async def uncertain_claim(session, project):
    row = SddActivityClaim(
        project_id=UUID(project["id"]),
        request_id=uuid4(),
        actor="operator",
        request_digest="0" * 64,
        unit="docs/proposals/PROP-demo",
        activity="dev",
        checkpoint={"uncertain": True, "branch": "dev-demo", "pull_number": 7},
    )
    session.add(row)
    await session.commit()
    return row


async def test_claim_acknowledgment_requires_exact_evidence_and_is_idempotent(client, project, session, github):
    row = await uncertain_claim(session, project)
    root = f"/api/v1/projects/{project['id']}/sdd/claims/{row.id}"
    evidence = (await client.get(root)).json()
    assert not evidence["settled"]
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

    claim = await uncertain_claim(session, project)
    candidate = {
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
    assert not evidence["settled"]
    body = {
        "request_id": str(uuid4()),
        "expected_checkpoint_digest": evidence["checkpoint_digest"],
        "acknowledge_external_work": True,
    }
    github.paths.clear()
    response = await client.post(root + "/reconcile", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["settled"]
    assert response.json()["checkpoint"]["initial_sha"] == candidate["initial_sha"]
    assert response.json()["checkpoint"]["branch"] == candidate["branch"]
    assert response.json()["run_id"] is None
    assert (await client.post(root + "/reconcile", json=body)).json() == response.json()
    assert github.paths == []


@pytest.mark.parametrize("reason", ["live-lease", "known-outcome", "run-owner"])
async def test_optimistic_settlement_refuses_current_authority(client, project, session, github, reason):
    from datetime import timedelta

    from app_testing_base import utc_now

    claim = await uncertain_claim(session, project)
    checkpoint = {"uncertain": reason != "known-outcome"}
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


async def test_uncertain_original_start_exposes_exact_claim_recovery(client, project, session, monkeypatch):
    from unittest.mock import AsyncMock

    from app.features.project_management.projects.errors import ProjectError
    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd import activities
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.schemas import StartActivityRequest

    projects = ProjectService(ProjectRepository())
    owner = await projects.get(session, UUID(project["id"]))
    claims = ActivityClaims(projects, AsyncMock(), AsyncMock())
    claim = await claims.reserve(session, owner, "dev", "demo", StartActivityRequest(request_id=uuid4()), "operator")
    claim_id = claim.id
    await session.commit()

    async def uncertain(*args, checkpoint, **kwargs):
        await checkpoint(initial_sha="b" * 40, branch="dev-demo", ref_attempted=True, pr_attempted=True)
        raise ProjectError(409, "Original activity PR outcome is uncertain", code="SDD_PUBLICATION_UNCERTAIN")

    monkeypatch.setattr(activities.ActivityStarter, "start", uncertain)
    for _ in range(2):
        with pytest.raises(ProjectError) as error:
            await claims.execute(owner.id, claim_id)
        assert error.value.status == 409 and error.value.code == "SDD_PUBLICATION_UNCERTAIN"
        assert f"/api/v1/projects/{owner.id}/sdd/claims/{claim_id}" in error.value.detail


async def test_openapi_contains_only_supported_sdd_surfaces(app):
    schema = app.openapi()
    sdd_paths = {path.split("/sdd", 1)[1] for path in schema["paths"] if "/sdd" in path}
    assert sdd_paths == {
        "/runs",
        "/proposals",
        "/proposals/{slug}/planning",
        "/proposals/{slug}/development",
        "/claims/{claim_id}",
        "/claims/{claim_id}/reconcile",
    }
    assert not any(path.endswith("/sdd-decisions") for path in schema["paths"])
    assert set(schema["components"]["schemas"]["ResumeRunRequest"]["properties"]) == {
        "request_id",
        "expected_revision",
        "answer_id",
    }

    assert not {"plan_accept_open", "decided"} & set(schema["components"]["schemas"]["ProposalRun"]["properties"])


@pytest.mark.parametrize("deferred", [False, True])
@pytest.mark.parametrize("activity", ["planning", "development"])
async def test_bound_activity_starts_without_another_tick(
    client, project, github, monkeypatch, activity, mention_github, deferred
):
    from app.features.project_management.pipeline_runs.schemas import EnrollPullRequest
    from app.features.project_management.sdd.activities import ActivityStarter
    from app_layer_base.core.database.transaction import AsyncTransaction

    comments = mention_github
    if deferred:
        from unittest.mock import AsyncMock

        from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
        from app.features.project_management.projects.errors import ProjectError

        monkeypatch.setattr(PipelineRunUseCase, "advance_until_wait", AsyncMock(side_effect=ProjectError(409, "held")))
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"expected_revision": project["revision"], "project_type": "sdd"},
    )
    assert changed.status_code == 200, changed.text
    github.pulls[7]["head"]["ref"] = "plan-demo" if activity == "planning" else "dev-demo"
    github.pulls[7]["draft"] = True

    async def published(self, owner, kind, slug, request, actor, *, admission, **kwargs):
        enrollment = EnrollPullRequest(pull_number=7, spec_dir="docs/proposals/PROP-demo", handoff=kind == "dev")
        await kwargs["checkpoint"](
            branch=github.pulls[7]["head"]["ref"],
            pull_number=7,
            initial_sha=github.pulls[7]["head"]["sha"],
            enrollment_request=enrollment.model_dump(mode="json"),
        )
        return await self.runs.enroll(owner.id, enrollment, admission=admission)

    monkeypatch.setattr(ActivityStarter, "start", published)
    response = await client.post(
        f"/api/v1/projects/{project['id']}/sdd/proposals/demo/{activity}",
        json={"request_id": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    assert response.json()["state"] == ("queued" if deferred else "implementing")
    assert len(comments) == (0 if deferred else 1)
    async with AsyncTransaction() as session:
        from sqlalchemy import select

        claim = await session.scalar(
            select(SddActivityClaim).where(SddActivityClaim.run_id == UUID(response.json()["id"]))
        )
        assert claim is not None and not claim.checkpoint["uncertain"]


@pytest.mark.parametrize("published", [False, True])
async def test_crashed_worker_claim_is_released_or_reconcilable_after_project_change(
    client, project, session, published
):
    """A worker that died without recording an outcome must not leave the unit owned forever."""
    from datetime import timedelta
    from unittest.mock import AsyncMock

    from app.features.project_management.projects.errors import ProjectError
    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.schemas import StartActivityRequest
    from app_testing_base import utc_now

    projects = ProjectService(ProjectRepository())
    claims = ActivityClaims(projects, AsyncMock(), AsyncMock())
    owner = await projects.get(session, UUID(project["id"]))
    claim = await claims.reserve(session, owner, "dev", "demo", StartActivityRequest(request_id=uuid4()), "operator")
    claim.checkpoint = {
        **claim.checkpoint,
        "lease": str(uuid4()),
        "lease_expires_at": (utc_now() - timedelta(seconds=1)).isoformat(),
        **({"ref_attempted": True, "branch": "dev-demo"} if published else {}),
    }
    owner.revision += 1
    claim_id = claim.id
    await session.commit()

    with pytest.raises(ProjectError, match="Project changed after activity claim") as refused:
        await claims.execute(owner.id, claim_id)
    assert refused.value.status == 409
    await session.refresh(claim)
    assert claim.run_id is None and claim.checkpoint.get("lease_expires_at") is None
    if not published:
        assert claim.settled and claim.checkpoint["refusal"]["status"] == 409
        await session.refresh(owner)
        replacement = await claims.reserve(
            session, owner, "dev", "demo", StartActivityRequest(request_id=uuid4()), "operator"
        )
        assert replacement.id != claim_id
        return
    assert not claim.settled and claim.checkpoint["uncertain"] is True
    root = f"/api/v1/projects/{project['id']}/sdd/claims/{claim_id}"
    evidence = (await client.get(root)).json()
    with pytest.raises(ProjectError, match="Project changed after activity claim"):
        await claims.execute(owner.id, claim_id)
    assert (await client.get(root)).json()["checkpoint_digest"] == evidence["checkpoint_digest"]
    response = await client.post(
        root + "/reconcile",
        json={
            "request_id": str(uuid4()),
            "expected_checkpoint_digest": evidence["checkpoint_digest"],
            "acknowledge_external_work": True,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["settled"]
