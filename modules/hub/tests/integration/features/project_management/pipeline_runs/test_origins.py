from uuid import UUID, uuid4

import pytest
from app.features.ai_catalogs.models import AICatalogSession
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.origin_reads import read_runs
from app.features.project_management.projects.models import Project
from app.features.project_management.sdd.batch_models import SddActivityClaim, SddBatch, SddBatchMember
from app.features.project_management.work_plans.models import WorkItem, WorkPlan
from sqlalchemy import event
from sqlalchemy.engine import Engine

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

project = scenarios.project
github = scenarios.github
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def seed_origins(session, project, run):
    owner = await session.get(Project, UUID(project["id"]))
    plan = WorkPlan(
        project_id=owner.id,
        title="Plan",
        description="",
        repository="owner/app",
        connector_id=owner.github_connector_id,
        base_branch="main",
    )
    session.add(plan)
    await session.flush()
    item = WorkItem(plan_id=plan.id, key="one", title="One", description="", acceptance="", pipeline_run_id=run.id)
    batch = SddBatch(
        project_id=owner.id,
        request_id=uuid4(),
        request_digest="0" * 64,
        actor="operator",
        basis={},
        evaluation={},
        exclusion=False,
    )
    session.add_all([item, batch])
    await session.flush()
    member = SddBatchMember(
        batch_id=batch.id, position=0, anchor_id="one", path="docs/proposals/PROP-one", initial={}, phase="dev"
    )
    session.add(member)
    await session.flush()
    sessions = [
        AICatalogSession(
            ai_catalog_id=run.ai_catalog_id,
            title=f"session-{i}",
            state="completed",
            pipeline_run_id=run.id,
            url="https://jules.google.com/session/one" if i == 0 else None,
        )
        for i in range(2)
    ]
    claims = [
        SddActivityClaim(
            project_id=owner.id,
            member_id=member.id if i == 0 else None,
            request_id=uuid4(),
            actor="operator",
            request_digest="1" * 64,
            unit=f"docs/proposals/PROP-{i}",
            activity="dev",
            settled=True,
            checkpoint={},
            run_id=run.id,
        )
        for i in range(2)
    ]
    session.add_all(sessions + claims)
    await session.commit()
    return item, plan, batch


async def test_origin_projection_agrees_across_reads_and_mutations(client, project, session, github):
    response = await scenarios.enroll(client, project)
    assert response.status_code == 201, response.text
    initial = response.json()
    assert initial["enrollment_source"] == "unknown" and initial["related_origins"] == []
    run = await session.get(PipelineRun, UUID(initial["id"]))
    item, plan, batch = await seed_origins(session, project, run)
    root = f"/api/v1/pipeline-runs/{run.id}"
    detail = (await client.get(root)).json()
    refs = detail["related_origins"]
    assert detail["enrollment_source"] == "multiple"
    assert len(refs) == 5
    assert refs == sorted(refs, key=lambda ref: (ref["kind"], ref["id"]))
    work = next(ref for ref in refs if ref["kind"] == "work_plan")
    assert work["id"] == str(item.id) and work["work_plan_id"] == str(plan.id)
    assert {ref["batch_id"] for ref in refs if ref["kind"] == "native_sdd"} == {str(batch.id), None}
    assert sum(bool(ref["url"]) for ref in refs if ref["kind"] == "provider_session") == 1
    page = (await client.get("/api/v1/pipeline-runs", params={"project_id": project["id"]})).json()
    assert page["total_count"] == 1 and page["items"][0]["related_origins"] == refs
    paused = await client.post(root + "/pause")
    assert paused.status_code == 200 and paused.json()["related_origins"] == refs
    run.sdd_snapshot = {"spec_dir": "docs/proposals/PROP-current"}
    await session.commit()
    unit = await client.get(
        f"/api/v1/projects/{project['id']}/sdd/runs", params={"spec_dir": "docs/proposals/PROP-current"}
    )
    assert unit.status_code == 200, unit.text
    assert unit.json()[0]["related_origins"] == refs


@pytest.mark.parametrize("size", [1, 8])
async def test_projection_uses_three_selects_one_connection_and_preserves_page(client, project, session, github, size):
    response = await scenarios.enroll(client, project)
    run = await session.get(PipelineRun, UUID(response.json()["id"]))
    await seed_origins(session, project, run)
    runs = [run]
    for i in range(1, size):
        copy = PipelineRun(
            project_id=run.project_id,
            ai_catalog_id=run.ai_catalog_id,
            project_revision=run.project_revision,
            pull_number=100 + i,
            pull_url=f"https://example.test/{i}",
            pull_snapshot=run.pull_snapshot,
            state="queued",
            branch=f"dev-{i}",
        )
        session.add(copy)
        runs.append(copy)
    await session.commit()
    # The caller already owns one connection. Projection neither opens another nor fans out.
    await session.connection()
    statements, checkouts = [], []

    def statement(conn, cursor, sql, params, context, many):
        if sql.lstrip().upper().startswith("SELECT"):
            statements.append(sql)

    def checkout(*args):
        checkouts.append(True)

    event.listen(Engine, "before_cursor_execute", statement)
    event.listen(Engine, "checkout", checkout)
    try:
        views = await read_runs(session, runs)
    finally:
        event.remove(Engine, "before_cursor_execute", statement)
        event.remove(Engine, "checkout", checkout)
    assert [view.id for view in views] == [row.id for row in runs]
    assert len(statements) == 3 and checkouts == []
    assert views[0].enrollment_source == "multiple"
    assert all(view.enrollment_source == "unknown" for view in views[1:])


async def test_snapshot_proves_native_binding_and_projection_errors_are_not_unknown(
    client, project, session, github, monkeypatch
):
    from app.features.project_management.pipeline_runs.origin_repos import RunOriginRepository

    run = await session.get(PipelineRun, UUID((await scenarios.enroll(client, project)).json()["id"]))
    run.sdd_snapshot = {"spec_dir": "docs/proposals/PROP-current"}
    await session.commit()
    [view] = await read_runs(session, [run])
    assert view.enrollment_source == "native_sdd" and view.related_origins == []

    async def fail(*args):
        raise RuntimeError("projection lookup failed")

    monkeypatch.setattr(RunOriginRepository, "sessions", fail)
    with pytest.raises(RuntimeError, match="projection lookup failed"):
        await read_runs(session, [run])


async def test_cross_project_reverse_owners_are_not_exposed(client, project, session, github):
    run = await session.get(PipelineRun, UUID((await scenarios.enroll(client, project)).json()["id"]))
    other = Project(name="Other project")
    session.add(other)
    await session.flush()
    owner = await session.get(Project, run.project_id)
    plan = WorkPlan(
        project_id=other.id,
        title="Other Plan",
        description="",
        repository="owner/app",
        connector_id=owner.github_connector_id,
        base_branch="main",
    )
    session.add(plan)
    await session.flush()
    session.add_all(
        [
            WorkItem(
                plan_id=plan.id, key="other", title="Other", description="", acceptance="", pipeline_run_id=run.id
            ),
            SddActivityClaim(
                project_id=other.id,
                request_id=uuid4(),
                actor="operator",
                request_digest="0" * 64,
                unit="docs/proposals/PROP-private",
                activity="dev",
                settled=True,
                checkpoint={},
                run_id=run.id,
            ),
        ]
    )
    await session.commit()
    [view] = await read_runs(session, [run])
    assert view.related_origins == [] and view.enrollment_source == "unknown"


async def test_old_batch_detail_is_project_scoped_and_observation_only(client, project, session, github):
    batches = [
        SddBatch(
            project_id=UUID(project["id"]),
            request_id=uuid4(),
            request_digest="0" * 64,
            actor="operator",
            basis={},
            evaluation={},
            exclusion=False,
            state="stopped",
        )
        for _ in range(55)
    ]
    session.add_all(batches)
    await session.commit()
    root = f"/api/v1/projects/{project['id']}/sdd/batches"
    latest = (await client.get(root)).json()
    old = next(row for row in batches if str(row.id) not in {entry["id"] for entry in latest})
    github.paths.clear()
    detail = await client.get(f"{root}/{old.id}")
    assert detail.status_code == 200 and detail.json()["id"] == str(old.id)
    wrong = await client.get(f"/api/v1/projects/{uuid4()}/sdd/batches/{old.id}")
    assert wrong.status_code == 404
    assert github.paths == []


async def test_run_http_page_keeps_one_request_checkout(client, project, session, github):
    run = await session.get(PipelineRun, UUID((await scenarios.enroll(client, project)).json()["id"]))
    await seed_origins(session, project, run)
    checkouts = []

    def checkout(*args):
        checkouts.append(True)

    event.listen(Engine, "checkout", checkout)
    try:
        response = await client.get("/api/v1/pipeline-runs", params={"project_id": project["id"]})
    finally:
        event.remove(Engine, "checkout", checkout)
    assert response.status_code == 200, response.text
    assert response.json()["total_count"] == 1
    assert len(checkouts) <= 1
