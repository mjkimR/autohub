"""Owner-confirmed Planning/handoff/merge releases exactly one sequential member."""

from copy import deepcopy
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from app.features.ai_catalogs.models import AICatalog
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.projects.models import Project
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService
from app.features.project_management.sdd import batch_evidence, milestones
from app.features.project_management.sdd.activity_claims import ActivityClaims
from app.features.project_management.sdd.batch_driver import BatchDriver
from app.features.project_management.sdd.batch_models import SddActivityClaim, SddBatchMember
from app.features.project_management.sdd.batch_usecases import SddBatchUseCase
from app.features.project_management.sdd.usecases import SddUseCase
from app_layer_base.core.database.transaction import AsyncTransaction
from sqlalchemy import select

from tests.integration.features.project_management.sdd.test_batches import github, payload, preview, project

__all__ = ["github", "project"]
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_exact_owner_phases_and_canonical_repair_release_only_next_member(client, project, monkeypatch):
    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    value = preview(project["id"])
    value["members"][0].update(status="draft", activity_kind="plan")
    edge = value["edges"][0]
    edge.update(path="docs/proposals/PROP-a/proposal.md", status="draft")
    a = {
        "id": "PROP-a",
        "path": value["members"][0]["path"],
        "status": "draft",
        "content_digest": "draft",
        "depends_on": [],
    }
    b = {
        "id": "PROP-b",
        "path": value["members"][1]["path"],
        "status": "accepted",
        "content_digest": "b",
        "depends_on": ["PROP-a"],
    }
    value["batch_basis"]["members"] = [a, b]
    evaluator = AsyncMock(side_effect=lambda *args, **kwargs: deepcopy(value))
    monkeypatch.setattr(milestones, "preview_milestone", evaluator)
    body = payload()
    next(row for row in body["members"] if row["id"] == "PROP-a")["activity"] = "plan"
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    response = await client.post(path, json=body)
    assert response.status_code == 201, response.text
    batch_id, project_id = UUID(response.json()["id"]), UUID(project["id"])
    execute = AsyncMock()
    monkeypatch.setattr(ActivityClaims, "execute", execute)
    observer = SimpleNamespace(get_pull_request=AsyncMock())
    driver = BatchDriver(
        SddBatchUseCase(
            ProjectService(ProjectRepository()), cast(SddUseCase, SimpleNamespace(observer=observer, run_use_case=None))
        )
    )
    await driver.tick(project_id, batch_id)
    assert execute.await_count == 1

    async def owner_run(phase, state, snapshot):
        async with AsyncTransaction() as session:
            claim = await session.scalar(
                select(SddActivityClaim).where(
                    SddActivityClaim.project_id == project_id, SddActivityClaim.activity == phase
                )
            )
            assert claim
            run_id = uuid4()
            p = await session.get(Project, project_id)
            assert p
            catalog_id = await session.scalar(select(AICatalog.id).limit(1))
            if catalog_id is None:
                catalog = AICatalog(key="batch-test", name="Batch test", kind="codex", adapter="codex_github_mention")
                session.add(catalog)
                await session.flush()
                catalog_id = catalog.id
            run = PipelineRun(
                id=run_id,
                project_id=project_id,
                ai_catalog_id=catalog_id,
                project_revision=p.revision,
                github_repository=p.github_repository,
                github_connector_id=p.github_connector_id,
                pull_number=42 if phase == "plan" else (43 if claim.unit.endswith("PROP-a") else 44),
                pull_url="https://github.com/owner/app/pull/42",
                pull_snapshot={},
                state=state,
                branch=f"{phase}-{claim.unit.rsplit('PROP-', 1)[1]}",
                sdd_snapshot=snapshot,
                sdd_progress={"unit_status": "accepted" if phase == "plan" else "completed"},
            )
            session.add(run)
            claim.run_id = run_id
        return run_id

    plan_run = await owner_run("plan", "implementing", {"spec_dir": "docs/proposals/PROP-a"})
    await driver.tick(project_id, batch_id)
    assert execute.await_count == 1  # A worker finishing is not confirmed owner merge.
    async with AsyncTransaction() as session:
        run = await session.get(PipelineRun, plan_run)
        assert run
        run.state = "completed"
    observer.get_pull_request.return_value = {"merged": False, "head": {"ref": "plan-a"}, "base": {"ref": "main"}}
    await driver.tick(project_id, batch_id)
    assert execute.await_count == 1
    accepted = {**a, "status": "accepted", "content_digest": "reviewed-accepted"}
    monkeypatch.setattr(batch_evidence, "accepted_proposal", AsyncMock(return_value=accepted))
    observer.get_pull_request.return_value = {
        "merged": True,
        "merge_commit_sha": "c" * 40,
        "head": {"ref": "plan-a"},
        "base": {"ref": "main"},
    }
    await driver.tick(project_id, batch_id)
    value["members"][0].update(status="accepted", activity_kind="dev")
    value["batch_basis"]["members"][0] = accepted
    await driver.tick(project_id, batch_id)
    assert execute.await_count == 2  # Same member's Development; B is still waiting.
    await owner_run(
        "dev", "completed", {"spec_dir": "specs/2026-11/20261106-a", "handoff_from": "docs/proposals/PROP-a"}
    )
    target = {"id": "SPEC-a", "path": "specs/2026-11/20261106-a/spec.md", "observed_sha": "d" * 40}
    monkeypatch.setattr(batch_evidence, "completed_spec", AsyncMock(return_value=None))
    observer.get_pull_request.return_value = {
        "merged": True,
        "merge_commit_sha": "d" * 40,
        "head": {"ref": "dev-a"},
        "base": {"ref": "main"},
    }
    await driver.tick(project_id, batch_id)
    assert execute.await_count == 2  # Exact completed SPEC on selected base is also necessary.
    monkeypatch.setattr(batch_evidence, "completed_spec", AsyncMock(return_value=target))
    await driver.tick(project_id, batch_id)
    # Native handoff removes A but cannot itself rewrite another member's PROP dependency.
    value["members"] = value["members"][1:]
    value["batch_basis"]["members"] = [b]
    value["complete"] = False
    value["reasons"] = ["Missing PROP-a; canonical repair required"]
    await driver.tick(project_id, batch_id)
    assert execute.await_count == 2
    current = (await client.get(path + f"/{batch_id}")).json()
    assert current["state"] == "attention"
    response = await client.post(
        path + f"/{batch_id}/controls",
        json={"request_id": str(uuid4()), "expected_revision": current["revision"], "action": "resume"},
    )
    assert response.status_code == 200
    value.update(complete=True, reasons=[])
    value["members"][0].update(eligibility="eligible_now", scheduling="pass")
    value["batch_basis"]["members"][0] = {**b, "depends_on": ["SPEC-a"]}
    value["edges"] = [
        {
            "source": "PROP-b",
            "requested_id": "SPEC-a",
            "canonical_id": "SPEC-a",
            "path": target["path"],
            "status": "completed",
        }
    ]
    await driver.tick(project_id, batch_id)
    assert execute.await_count == 3
    async with AsyncTransaction() as session:
        member = await session.scalar(
            select(SddBatchMember).where(SddBatchMember.batch_id == batch_id, SddBatchMember.anchor_id == "PROP-a")
        )
        assert (
            member
            and member.state == "succeeded"
            and member.spec_anchor is not None
            and member.spec_anchor["id"] == "SPEC-a"
        )

    await owner_run(
        "dev", "completed", {"spec_dir": "specs/2026-11/20261106-b", "handoff_from": "docs/proposals/PROP-b"}
    )
    monkeypatch.setattr(
        batch_evidence,
        "completed_spec",
        AsyncMock(return_value={"id": "SPEC-b", "path": "specs/2026-11/20261106-b/spec.md", "observed_sha": "e" * 40}),
    )
    observer.get_pull_request.return_value = {
        "merged": True,
        "merge_commit_sha": "e" * 40,
        "head": {"ref": "dev-b"},
        "base": {"ref": "main"},
    }
    await driver.tick(project_id, batch_id)
    completed = (await client.get(path + f"/{batch_id}")).json()
    assert completed["state"] == "completed" and not completed["exclusion"]
    assert all(member["state"] == "succeeded" for member in completed["members"])
