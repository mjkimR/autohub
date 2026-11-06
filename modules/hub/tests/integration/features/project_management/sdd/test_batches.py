"""Durable selection/control receipts at the authenticated HTTP/real transaction boundary."""

from copy import deepcopy
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import milestones
from app.features.project_management.sdd.batch_policy import ordered_selection
from app.features.project_management.sdd.usecases import SddUseCase

from tests.integration.features.project_management.pipeline_runs import test_merge_stage as merge
from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

github = merge.github
project = scenarios.project
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.fixture(autouse=True)
def batch_head(monkeypatch):
    from app.features.project_management.sdd import batch_evidence

    reader = AsyncMock(return_value="a" * 40)
    monkeypatch.setattr(batch_evidence, "remote_head", reader)
    return reader


def preview(project_id):
    return {
        "project_id": project_id,
        "repository": "owner/repo",
        "requested_ref": "main",
        "resolved_sha": "a" * 40,
        "milestone": {"id": "MS-demo", "path": "docs/roadmap/MS-demo.md"},
        "observed_at": "2026-11-06T00:00:00Z",
        "runtime_identity": "fixture",
        "complete": True,
        "counts": {"members": 2, "anchors": 2, "edges": 1},
        "limits": {},
        "reasons": [],
        "warnings": [],
        "nodes": [],
        "edges": [{"source": "PROP-b", "requested_id": "PROP-a", "canonical_id": "PROP-a"}],
        "members": [
            {
                "id": f"PROP-{key}",
                "path": f"docs/proposals/PROP-{key}/proposal.md",
                "title": key,
                "status": "accepted",
                "activity_kind": "dev",
                "admission": "pass",
                "scheduling": "pass" if key == "a" else "held",
                "eligibility": "eligible_now" if key == "a" else "held",
                "workflow_hold": {},
                "reasons": [],
            }
            for key in ("a", "b")
        ],
        "batch_basis": {"configuration": {}, "runtime": {}, "policy": {}, "members": []},
    }


def payload():
    return {
        "request_id": str(uuid4()),
        "ref": "main",
        "milestone_id": "MS-demo",
        "expected_sha": "a" * 40,
        "through_development": True,
        "members": [
            {"id": f"PROP-{key}", "path": f"docs/proposals/PROP-{key}/proposal.md", "activity": "dev"}
            for key in ("b", "a")
        ],
    }


async def test_durable_order_replay_and_controls_preserve_later_stop(client, project, monkeypatch):
    result = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    assert result.status_code == 200
    evaluator = AsyncMock(return_value=preview(project["id"]))
    monkeypatch.setattr(milestones, "preview_milestone", evaluator)
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    body = payload()
    response = await client.post(path, json=body)
    assert response.status_code == 201, response.text
    batch = response.json()
    assert [m["anchor_id"] for m in batch["members"]] == ["PROP-a", "PROP-b"]
    assert batch["state"] == "running"
    assert batch["members"][0]["initial"]["effective_preferences"]["dev_effort"] == "medium"
    replay = await client.post(path, json=body)
    assert replay.json()["id"] == batch["id"]
    assert evaluator.await_count == 1
    changed = await client.post(path, json={**body, "ref": "other"})
    assert changed.status_code == 409
    control_path = path + f"/{batch['id']}/controls"
    pause = {"request_id": str(uuid4()), "expected_revision": 1, "action": "pause"}
    response = await client.post(control_path, json=pause)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "paused"
    stop = {"request_id": str(uuid4()), "expected_revision": response.json()["revision"], "action": "stop"}
    response = await client.post(control_path, json=stop)
    assert response.status_code == 200
    assert not response.json()["exclusion"]
    replay = await client.post(control_path, json=pause)
    assert replay.json()["state"] == "stopped"
    assert (await client.post(control_path, json={**pause, "request_id": str(uuid4())})).status_code == 409
    assert (await client.get(path)).json()[0]["id"] == batch["id"]
    assert (await client.get(f"/api/v1/projects/{uuid4()}/sdd/batches/{batch['id']}")).status_code == 404
    runs = await client.get("/api/v1/pipeline-runs", params={"project_id": project["id"]})
    assert not runs.json()["items"]


async def test_stale_and_incomplete_selection_has_no_persisted_effect(client, project, monkeypatch):
    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    value = preview(project["id"])
    evaluator = AsyncMock(return_value=value)
    monkeypatch.setattr(milestones, "preview_milestone", evaluator)
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    body = payload()
    assert (await client.post(path, json={**body, "expected_sha": "b" * 40})).status_code == 409
    value["complete"] = False
    assert (await client.post(path, json=body)).status_code == 422
    assert (await client.get(path)).json() == []


@pytest.mark.parametrize("key,limit", [("members", 50), ("anchors", 200), ("edges", 500)])
async def test_selection_count_limits_are_strict(key, limit):
    value, body = preview("fixture"), payload()
    value["counts"][key] = limit
    assert len(ordered_selection(value, body["members"])) == 2
    value["counts"][key] = limit + 1
    with pytest.raises(ProjectError):
        ordered_selection(value, body["members"])


async def test_workflow_hold_and_cycle_never_become_future_intent():
    value, body = preview("fixture"), payload()
    value["members"][0]["workflow_hold"] = {"blocked": True}
    with pytest.raises(ProjectError):
        ordered_selection(value, body["members"])
    value = deepcopy(preview("fixture"))
    value["edges"].append({"source": "PROP-a", "canonical_id": "PROP-b"})
    with pytest.raises(ProjectError):
        ordered_selection(value, body["members"])


@pytest.mark.parametrize("control_first", [True, False])
async def test_claim_control_linearization_preserves_exact_inflight_identity(
    client, project, monkeypatch, control_first
):
    from types import SimpleNamespace
    from uuid import UUID

    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.batch_driver import BatchDriver
    from app.features.project_management.sdd.batch_usecases import SddBatchUseCase

    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    monkeypatch.setattr(milestones, "preview_milestone", AsyncMock(return_value=preview(project["id"])))
    execute = AsyncMock()
    monkeypatch.setattr(ActivityClaims, "execute", execute)
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    batch = (await client.post(path, json=payload())).json()
    driver = BatchDriver(
        SddBatchUseCase(
            ProjectService(ProjectRepository()), cast(SddUseCase, SimpleNamespace(observer=None, run_use_case=None))
        )
    )
    if not control_first:
        await driver.tick(UUID(project["id"]), UUID(batch["id"]))
        batch = (await client.get(path + f"/{batch['id']}")).json()
        assert execute.await_count == 1
    response = await client.post(
        path + f"/{batch['id']}/controls",
        json={"request_id": str(uuid4()), "expected_revision": batch["revision"], "action": "stop"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["exclusion"] is (not control_first)
    await driver.tick(UUID(project["id"]), UUID(batch["id"]))
    if control_first:
        execute.assert_not_called()
    else:
        assert execute.await_count == 2
        assert execute.await_args_list[0] == execute.await_args_list[1]


async def test_runtime_or_remaining_content_drift_holds_without_claim(client, project, monkeypatch):
    from types import SimpleNamespace
    from uuid import UUID

    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.batch_driver import BatchDriver
    from app.features.project_management.sdd.batch_usecases import SddBatchUseCase

    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    original = preview(project["id"])
    monkeypatch.setattr(milestones, "preview_milestone", AsyncMock(return_value=original))
    execute = AsyncMock()
    monkeypatch.setattr(ActivityClaims, "execute", execute)
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    batch = (await client.post(path, json=payload())).json()
    changed = deepcopy(original)
    changed["batch_basis"]["runtime"] = {"version": "changed"}
    monkeypatch.setattr(milestones, "preview_milestone", AsyncMock(return_value=changed))
    driver = BatchDriver(
        SddBatchUseCase(
            ProjectService(ProjectRepository()), cast(SddUseCase, SimpleNamespace(observer=None, run_use_case=None))
        )
    )
    await driver.tick(UUID(project["id"]), UUID(batch["id"]))
    current = (await client.get(path + f"/{batch['id']}")).json()
    assert current["state"] == "attention"
    assert "Runtime" in current["detail"]
    execute.assert_not_called()


async def test_simultaneous_postgres_ticks_commit_one_claim(client, project, monkeypatch, session):
    import asyncio
    from types import SimpleNamespace
    from uuid import UUID

    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.batch_driver import BatchDriver
    from app.features.project_management.sdd.batch_usecases import SddBatchUseCase

    if session.get_bind().dialect.name != "postgresql":
        pytest.skip("Multi-connection row-lock evidence requires PostgreSQL")
    await session.commit()
    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    value = preview(project["id"])
    evaluator = AsyncMock(return_value=value)
    monkeypatch.setattr(milestones, "preview_milestone", evaluator)
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    batch = (await client.post(path, json=payload())).json()
    barrier = asyncio.Barrier(2)

    async def evaluate(*args, **kwargs):
        await barrier.wait()
        return deepcopy(value)

    evaluator.side_effect = evaluate
    execute = AsyncMock()
    monkeypatch.setattr(ActivityClaims, "execute", execute)
    driver = BatchDriver(
        SddBatchUseCase(
            ProjectService(ProjectRepository()), cast(SddUseCase, SimpleNamespace(observer=None, run_use_case=None))
        )
    )
    await asyncio.wait_for(asyncio.gather(*(driver.tick(UUID(project["id"]), UUID(batch["id"])) for _ in range(2))), 10)
    assert execute.await_count == 1
    current = (await client.get(path + f"/{batch['id']}")).json()
    assert len(current["members"][0]["claims"]) == 1
    assert not current["members"][1]["claims"]


@pytest.mark.parametrize("change", ["milestone_graph", "post_planning_body"])
async def test_reviewed_graph_and_post_planning_content_drift_is_refused(client, project, monkeypatch, change):
    from types import SimpleNamespace
    from uuid import UUID

    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.batch_driver import BatchDriver
    from app.features.project_management.sdd.batch_models import SddBatchMember
    from app.features.project_management.sdd.batch_usecases import SddBatchUseCase
    from app_layer_base.core.database.transaction import AsyncTransaction
    from sqlalchemy import select

    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    original = preview(project["id"])
    a = {
        "id": "PROP-a",
        "path": original["members"][0]["path"],
        "status": "accepted",
        "content_digest": "original",
        "depends_on": [],
    }
    original["batch_basis"]["members"] = [a]
    original["edges"].append(
        {
            "source": "MS-demo",
            "requested_id": "MS-prerequisite",
            "canonical_id": "MS-prerequisite",
            "path": "docs/roadmap/MS-prerequisite.md",
        }
    )
    monkeypatch.setattr(milestones, "preview_milestone", AsyncMock(return_value=original))
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    batch = (await client.post(path, json=payload())).json()
    fresh = deepcopy(original)
    if change == "milestone_graph":
        fresh["edges"] = fresh["edges"][:1]
    else:
        async with AsyncTransaction() as session:
            member = await session.scalar(
                select(SddBatchMember).where(
                    SddBatchMember.batch_id == UUID(batch["id"]), SddBatchMember.anchor_id == "PROP-a"
                )
            )
            assert member
            member.outcome = {
                "planning_merge": {"merge_sha": "c" * 40},
                "accepted_basis": {**a, "content_digest": "accepted"},
            }
        fresh["batch_basis"]["members"][0]["content_digest"] = "later-unrelated-scope-edit"
    driver = BatchDriver(
        SddBatchUseCase(
            ProjectService(ProjectRepository()), cast(SddUseCase, SimpleNamespace(observer=None, run_use_case=None))
        )
    )
    reason = await driver._compare(UUID(project["id"]), UUID(batch["id"]), batch["revision"], batch["basis"], fresh)
    assert reason is not None
    assert ("graph" in reason) if change == "milestone_graph" else ("content/scope" in reason)


@pytest.mark.parametrize(
    "winner,contender", [("batch", "single"), ("single", "batch"), ("batch", "stop"), ("stop", "batch")]
)
async def test_postgres_cross_entry_and_control_races(client, project, monkeypatch, session, winner, contender):
    import asyncio
    from uuid import UUID

    from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
    from app.features.project_management.pipelines.services import PipelineObservationService
    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.batch_driver import BatchDriver
    from app.features.project_management.sdd.batch_models import SddActivityClaim
    from app.features.project_management.sdd.batch_usecases import SddBatchUseCase
    from app.features.project_management.sdd.schemas import StartActivityRequest
    from app_layer_base.core.database.transaction import AsyncTransaction
    from sqlalchemy import select

    if session.get_bind().dialect.name != "postgresql":
        pytest.skip("Cross-entry row-lock evidence requires PostgreSQL")
    await session.commit()
    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    value = preview(project["id"])
    monkeypatch.setattr(milestones, "preview_milestone", AsyncMock(return_value=value))
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    batch = (await client.post(path, json=payload())).json()
    project_id, batch_id = UUID(project["id"]), UUID(batch["id"])
    projects = ProjectService(ProjectRepository())
    sdd = SddUseCase(projects, cast(PipelineObservationService, None), cast(PipelineRunUseCase, None))
    driver = BatchDriver(SddBatchUseCase(projects, sdd))
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def execute(self, project_id, claim_id):
        calls.append(claim_id)
        entered.set()
        await release.wait()

    monkeypatch.setattr(ActivityClaims, "execute", execute)

    async def single():
        await sdd.start_activity(project_id, "dev", "a", StartActivityRequest(request_id=uuid4()), "user:operator")

    async def stop():
        response = await client.post(
            path + f"/{batch_id}/controls",
            json={
                "request_id": str(uuid4()),
                "expected_revision": (await client.get(path + f"/{batch_id}")).json()["revision"],
                "action": "stop",
            },
        )
        assert response.status_code == 200
        return response.json()

    if winner == "batch":
        task = asyncio.create_task(driver.tick(project_id, batch_id))
        await asyncio.wait_for(entered.wait(), 5)
        if contender == "single":
            with pytest.raises(ProjectError):
                await single()
        else:
            stopped = await stop()
            assert stopped["exclusion"]
        release.set()
        await task
    else:

        async def evaluate(*args, **kwargs):
            entered.set()
            await release.wait()
            return deepcopy(value)

        monkeypatch.setattr(milestones, "preview_milestone", evaluate)
        task = asyncio.create_task(driver.tick(project_id, batch_id))
        await asyncio.wait_for(entered.wait(), 5)
        if winner == "single":
            # Let the single owner commit its reservation while batch evaluation is paused.
            # Commit the individual reservation while the competing batch's evaluation is held.
            async with AsyncTransaction() as tx:
                p = await projects.get(tx, project_id, lock=True)
                claims = ActivityClaims(projects, None, None)
                await claims.reserve(tx, p, "dev", "a", StartActivityRequest(request_id=uuid4()), "user:operator")
            release.set()
            with pytest.raises(ProjectError):
                await task
        else:
            stopped = await stop()
            assert not stopped["exclusion"]
            release.set()
            await task
    async with AsyncTransaction() as tx:
        claims = list(await tx.scalars(select(SddActivityClaim).where(SddActivityClaim.project_id == project_id)))
        assert len(claims) == (0 if winner == "stop" else 1)
        assert len(calls) <= 1


@pytest.mark.parametrize("stage", ["create", "claim"])
async def test_remote_head_movement_before_commit_refuses_stale_state(client, project, monkeypatch, batch_head, stage):
    from types import SimpleNamespace
    from uuid import UUID

    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.batch_driver import BatchDriver
    from app.features.project_management.sdd.batch_usecases import SddBatchUseCase

    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    value = preview(project["id"])
    monkeypatch.setattr(milestones, "preview_milestone", AsyncMock(return_value=value))
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    if stage == "create":
        batch_head.return_value = "b" * 40
        assert (await client.post(path, json=payload())).status_code == 409
        assert not (await client.get(path)).json()
    else:
        batch = (await client.post(path, json=payload())).json()
        batch_head.return_value = "b" * 40
        execute = AsyncMock()
        monkeypatch.setattr(ActivityClaims, "execute", execute)
        driver = BatchDriver(
            SddBatchUseCase(
                ProjectService(ProjectRepository()), cast(SddUseCase, SimpleNamespace(observer=None, run_use_case=None))
            )
        )
        await driver.tick(UUID(project["id"]), UUID(batch["id"]))
        current = (await client.get(path + f"/{batch['id']}")).json()
        assert not current["members"][0]["claims"] and "Base moved" in current["detail"]
        execute.assert_not_called()


@pytest.mark.parametrize("rewrite", [False, True])
async def test_external_exact_canonical_alias_and_edge_only_repair_are_accepted(client, project, monkeypatch, rewrite):
    from types import SimpleNamespace
    from uuid import UUID

    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.batch_driver import BatchDriver
    from app.features.project_management.sdd.batch_usecases import SddBatchUseCase

    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    value = preview(project["id"])
    old_edge = {
        "source": "PROP-b",
        "requested_id": "PROP-external",
        "canonical_id": "PROP-external",
        "path": "docs/proposals/PROP-external/proposal.md",
        "status": "accepted",
    }
    value["edges"] = [old_edge]
    value["batch_basis"]["members"] = [
        {
            "id": "PROP-b",
            "path": value["members"][1]["path"],
            "status": "accepted",
            "content_digest": "unchanged",
            "depends_on": ["PROP-external"],
        }
    ]
    monkeypatch.setattr(milestones, "preview_milestone", AsyncMock(return_value=value))
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    batch = (await client.post(path, json=payload())).json()
    fresh = deepcopy(value)
    resolved = {
        "id": "SPEC-external",
        "kind": "spec",
        "status": "completed",
        "path": "specs/2026-11/20261106-external/spec.md",
    }
    fresh["nodes"] = [resolved]
    fresh["batch_basis"]["canonical_resolutions"] = {"PROP-external": resolved}
    fresh["edges"] = [
        {
            "source": "PROP-b",
            "requested_id": "SPEC-external" if rewrite else "PROP-external",
            "canonical_id": "SPEC-external",
            "path": resolved["path"],
            "status": "completed",
        }
    ]
    if rewrite:
        fresh["batch_basis"]["members"][0]["depends_on"] = ["SPEC-external"]
    driver = BatchDriver(
        SddBatchUseCase(
            ProjectService(ProjectRepository()), cast(SddUseCase, SimpleNamespace(observer=None, run_use_case=None))
        )
    )
    assert (
        await driver._compare(UUID(project["id"]), UUID(batch["id"]), batch["revision"], batch["basis"], fresh) is None
    )
    fresh["batch_basis"]["canonical_resolutions"] = {}
    assert await driver._compare(UUID(project["id"]), UUID(batch["id"]), batch["revision"], batch["basis"], fresh)


async def test_refusal_resume_acknowledgement_survives_wait_then_admission(client, project, monkeypatch):
    from types import SimpleNamespace
    from uuid import UUID

    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.sdd.activity_claims import ActivityClaims
    from app.features.project_management.sdd.batch_driver import BatchDriver
    from app.features.project_management.sdd.batch_models import SddActivityClaim
    from app.features.project_management.sdd.batch_usecases import SddBatchUseCase
    from app_layer_base.core.database.transaction import AsyncTransaction

    await client.patch(
        f"/api/v1/projects/{project['id']}", json={"expected_revision": project["revision"], "project_type": "sdd"}
    )
    value = preview(project["id"])
    monkeypatch.setattr(milestones, "preview_milestone", AsyncMock(side_effect=lambda *args, **kwargs: deepcopy(value)))
    path = f"/api/v1/projects/{project['id']}/sdd/batches"
    batch = (await client.post(path, json=payload())).json()
    async with AsyncTransaction() as tx:
        claim = SddActivityClaim(
            project_id=UUID(project["id"]),
            member_id=UUID(batch["members"][0]["id"]),
            request_id=uuid4(),
            actor="user:operator",
            request_digest="0" * 64,
            unit="docs/proposals/PROP-a",
            activity="dev",
            settled=True,
            checkpoint={"refusal": {"status": 409, "detail": "Fresh basis required"}},
        )
        tx.add(claim)
    driver = BatchDriver(
        SddBatchUseCase(
            ProjectService(ProjectRepository()), cast(SddUseCase, SimpleNamespace(observer=None, run_use_case=None))
        )
    )
    await driver.tick(UUID(project["id"]), UUID(batch["id"]))
    current = (await client.get(path + f"/{batch['id']}")).json()
    assert current["state"] == "attention"
    response = await client.post(
        path + f"/{batch['id']}/controls",
        json={"request_id": str(uuid4()), "expected_revision": current["revision"], "action": "resume"},
    )
    assert response.status_code == 200
    value["members"][0].update(eligibility="held", scheduling="held", reasons=["Prerequisite remains waiting"])
    await driver.tick(UUID(project["id"]), UUID(batch["id"]))
    await driver.tick(UUID(project["id"]), UUID(batch["id"]))
    current = (await client.get(path + f"/{batch['id']}")).json()
    assert current["state"] == "running" and current["evaluation"]["reviewed_refusal"] == str(claim.id)
    execute = AsyncMock()
    monkeypatch.setattr(ActivityClaims, "execute", execute)
    value["members"][0].update(eligibility="eligible_now", scheduling="pass", reasons=[])
    await driver.tick(UUID(project["id"]), UUID(batch["id"]))
    execute.assert_awaited_once()
