import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from app.features.project_management.pipeline_runs.models import ExecutionAttempt, ExecutionDelivery, PipelineRun
from app.features.project_management.work_plans.models import WorkItem, WorkItemRecovery, WorkItemRecoveryEvent
from app.features.project_management.work_plans.recovery_tick import RecoveryTick
from app_testing_base import utc_now
from sqlalchemy import func, select
from tests.integration.features.project_management.work_plans.test_work_plans import control, create, due, get, spec

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


def endpoint(project, plan, item):
    return f"/api/v1/projects/{project['id']}/work-plans/{plan['id']}/items/{item['id']}"


def command(plan, item):
    return dict(
        request_id=str(uuid4()),
        expected_revision=plan["revision"],
        expected_run_revision=item["recovery"]["run_revision"],
        reason="Repair verified",
    )


async def failed_preparation(client, setup_work):
    project, github, worker, _ = setup_work
    plan = await create(client, project)
    github.refs.pop("main")
    await worker.advance_project(UUID(project["id"]))
    plan = await get(client, project, plan)
    assert plan["items"][0]["state"] == "preparation_failed"
    return project, github, worker, plan, plan["items"][0]


async def test_preparation_recovery_replay_conflict_and_history(client, setup_work, session):
    project, github, worker, plan, item = await failed_preparation(client, setup_work)
    root = endpoint(project, plan, item)
    data = command(plan, item)
    accepted = await client.post(root + "/recover", json=data)
    assert accepted.status_code == 200, accepted.text
    replay = await client.post(root + "/recover", json=data)
    assert replay.status_code == 200
    assert replay.json()["recovery"]["id"] == accepted.json()["recovery"]["id"]
    assert (await client.post(root + "/recover", json=data | {"reason": "changed"})).status_code == 409
    assert (await client.post(root + "/recover", json=data | {"request_id": str(uuid4())})).status_code == 409
    github.refs["main"] = "d" * 40
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    current = await get(client, project, plan)
    assert current["items"][0]["id"] == item["id"]
    assert current["items"][0]["state"] == "running", current
    assert current["items"][1]["state"] == "waiting"
    history = (await client.get(root + "/recoveries")).json()
    assert history["total_count"] == 1
    record = history["items"][0]
    assert record["prior_outcome"]["state"] == "preparation_failed"
    assert record["prior_outcome"]["repository"] == "owner/app"
    assert record["prior_outcome"]["target_branch"] == "main"
    assert record["state"] == "running"
    assert [e["kind"] for e in record["events"]] == ["accepted", "reconciling", "awaiting-admission", "running"]
    assert len(github.pulls) == 1


@pytest.mark.parametrize("reason", ["", " ", "a" * 501])
async def test_recovery_reason_validation(client, setup_work, reason):
    project, _, _, plan, item = await failed_preparation(client, setup_work)
    response = await client.post(
        endpoint(project, plan, item) + "/recover", json=command(plan, item) | {"reason": reason}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("action", ["pause", "revoke"])
async def test_control_between_acceptance_and_reconcile_sends_nothing(client, setup_work, session, action):
    project, github, worker, plan, item = await failed_preparation(client, setup_work)
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    await control(client, project, await get(client, project, plan), action)
    github.refs["main"] = "d" * 40
    before = len(github.requests)
    await worker.advance_project(UUID(project["id"]))
    record = (await client.get(root + "/recoveries")).json()["items"][0]
    assert record["state"] == "refused"
    assert not github.pulls
    assert len(github.requests) == before


async def test_stale_and_cross_item_request_identity(client, setup_work):
    project, _, _, plan, item = await failed_preparation(client, setup_work)
    data = command(plan, item)
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=data | {"expected_revision": 99})).status_code == 409
    assert (await client.post(root + "/recover", json=data)).status_code == 200
    other = endpoint(project, plan, plan["items"][1])
    assert (await client.post(other + "/recover", json=data)).status_code == 409


async def terminal(client, setup_work, session):
    project, github, worker, _ = setup_work
    plan = await create(client, project)
    await worker.advance_project(UUID(project["id"]))
    plan = await get(client, project, plan)
    item = await session.get(WorkItem, UUID(plan["items"][0]["id"]))
    run = await session.get(PipelineRun, item.pipeline_run_id)
    run.state, item.state = "failed", "failed"
    await session.commit()
    plan = await get(client, project, plan)
    return project, github, worker, plan, plan["items"][0], run


async def test_terminal_recovery_keeps_run_epoch_and_commits_delivery(client, setup_work, session):
    project, _github, worker, plan, item, run = await terminal(client, setup_work, session)
    original_id, epoch = run.id, run.epoch
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    await session.refresh(run)
    assert run.id == original_id and run.epoch == epoch
    assert run.state == "dispatching"
    attempts = list(await session.scalars(select(ExecutionAttempt).where(ExecutionAttempt.pipeline_run_id == run.id)))
    assert len(attempts) == 1
    deliveries = list(
        await session.scalars(select(ExecutionDelivery).where(ExecutionDelivery.execution_attempt_id == attempts[0].id))
    )
    assert len(deliveries) == 1 and deliveries[0].cause == "recovery"
    assert (await client.get(root + "/recoveries")).json()["items"][0]["state"] == "running"


@pytest.mark.parametrize("change", ["closed", "wrong_target", "foreign"])
async def test_terminal_remote_refusals(client, setup_work, session, change):
    project, github, worker, plan, item, _run = await terminal(client, setup_work, session)
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    if change == "closed":
        github.pulls[100]["state"] = "closed"
    elif change == "wrong_target":
        github.pulls[100]["base"]["ref"] = "different"
    else:
        github.pulls[100]["head"]["repo"]["full_name"] = "foreign/app"
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    record = (await client.get(root + "/recoveries")).json()["items"][0]
    assert record["state"] == "refused"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 0


async def test_merged_recovery_spends_no_delivery_and_releases_dependency(client, setup_work, session):
    project, github, worker, plan, item, _run = await terminal(client, setup_work, session)
    assert (await client.post(endpoint(project, plan, item) + "/recover", json=command(plan, item))).status_code == 200
    github.merge(100)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    current = await get(client, project, plan)
    assert current["items"][0]["state"] == "succeeded"
    assert current["items"][1]["state"] == "running"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 0


async def test_two_requests_race_postgres(client, setup_work, session):
    if session.bind.dialect.name != "postgresql":
        pytest.skip("requires actual PostgreSQL row locks")
    project, _, _, plan, item = await failed_preparation(client, setup_work)
    data = command(plan, item)
    responses = await asyncio.gather(
        *(
            client.post(endpoint(project, plan, item) + "/recover", json=d)
            for d in [data, data | {"request_id": str(uuid4())}]
        )
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert await session.scalar(select(func.count()).select_from(WorkItemRecovery)) == 1


async def seed_attempt(session, run, *, kind="implementation", number=1, posted=False, cause="initial", external=None):
    from app.features.project_management.pipeline_runs.requests import build_implementation_request

    request, digest, key = build_implementation_request(run, "owner/app")
    attempt = ExecutionAttempt(
        pipeline_run_id=run.id,
        attempt_number=number,
        epoch=run.epoch,
        kind=kind,
        state="failed",
        request_snapshot=request.model_dump(mode="json"),
        request_digest=digest,
        idempotency_key=key,
        failure_code="CANCELED",
        external_status=external,
    )
    session.add(attempt)
    await session.flush()
    delivery = ExecutionDelivery(
        execution_attempt_id=attempt.id,
        delivery_number=1,
        cause=cause,
        external_id=str(number) if posted else None,
        posted_at=utc_now() if posted else None,
    )
    session.add(delivery)
    await session.commit()
    return attempt, delivery


async def test_pushed_implementation_advances_ci_without_delivery(client, setup_work, session):
    project, github, worker, plan, item, run = await terminal(client, setup_work, session)
    await seed_attempt(session, run, posted=True)
    github.pulls[100]["head"]["sha"] = "e" * 40
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    await session.refresh(run)
    assert run.state == "awaiting_ci" and run.epoch == 1
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 1
    assert await session.scalar(select(func.count()).select_from(ExecutionAttempt)) == 2


async def test_uncertain_delivery_retains_identity_without_dispatch(client, setup_work, session, monkeypatch):
    from app.features.project_management.pipeline_runs.adapters.codex_github_mention import CodexGithubMentionAdapter

    project, _, worker, plan, item, run = await terminal(client, setup_work, session)
    attempt, delivery = await seed_attempt(session, run)
    lookup = AsyncMock(return_value=None)
    monkeypatch.setattr(CodexGithubMentionAdapter, "find_delivery", lookup)
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert (await client.get(root + "/recoveries")).json()["items"][0]["state"] == "reconciling"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 1
    assert lookup.call_args.args[2].correlation_marker == attempt.request_snapshot["correlation_marker"]
    await session.refresh(delivery)
    assert delivery.posted_at is None


async def test_epoch_budget_exhaustion_never_resets_or_dispatches(client, setup_work, session, monkeypatch):
    from app.features.project_management.pipeline_runs.adapters.base import AgentReply
    from app.features.project_management.pipeline_runs.adapters.codex_github_mention import CodexGithubMentionAdapter

    project, _, worker, plan, item, run = await terminal(client, setup_work, session)
    await seed_attempt(session, run, kind="ci-fix", number=1, posted=True)
    await seed_attempt(session, run, kind="ci-fix", number=2, posted=True)
    monkeypatch.setattr(
        CodexGithubMentionAdapter,
        "collect_replies",
        AsyncMock(
            return_value=[AgentReply("done", "chatgpt-codex-connector", utc_now(), "Finished unchanged work", False)]
        ),
    )
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    await session.refresh(run)
    assert run.epoch == 1 and run.state == "failed"
    assert (await client.get(root + "/recoveries")).json()["items"][0]["state"] == "refused"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 2


async def test_active_owner_wins_without_loser_delivery(client, setup_work, session):
    project, _, worker, plan, item, run = await terminal(client, setup_work, session)
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    session.add(
        PipelineRun(
            project_id=run.project_id,
            ai_catalog_id=run.ai_catalog_id,
            project_revision=run.project_revision,
            github_repository=run.github_repository,
            github_connector_id=run.github_connector_id,
            pull_number=run.pull_number,
            pull_url=run.pull_url,
            pull_snapshot=run.pull_snapshot,
            branch=run.branch,
            state="queued",
        )
    )
    await session.commit()
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert (await client.get(root + "/recoveries")).json()["items"][0]["state"] == "refused"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 0


async def test_activity_failure_rolls_back_recovery_and_revision(client, setup_work, session, monkeypatch):
    from app.features.project_management.work_plans import recovery

    project, _, _, plan, item = await failed_preparation(client, setup_work)
    monkeypatch.setattr(recovery, "record_change", AsyncMock(side_effect=RuntimeError("audit unavailable")))
    with pytest.raises(RuntimeError, match="audit unavailable"):
        await client.post(endpoint(project, plan, item) + "/recover", json=command(plan, item))
    assert (await get(client, project, plan))["revision"] == plan["revision"]
    assert await session.scalar(select(func.count()).select_from(WorkItemRecovery)) == 0
    assert await session.scalar(select(func.count()).select_from(WorkItemRecoveryEvent)) == 0


async def test_expired_recovery_observation_cannot_activate(client, setup_work, session):
    project, github, worker, plan, item, run = await terminal(client, setup_work, session)
    accepted = await client.post(endpoint(project, plan, item) + "/recover", json=command(plan, item))
    row = await session.get(WorkItemRecovery, UUID(accepted.json()["recovery"]["id"]))
    current = await session.get(WorkItem, UUID(item["id"]))
    current.lease_token, current.lease_expires_at = uuid4(), utc_now() - timedelta(seconds=1)
    row.lease_generation = 3
    token = current.lease_token
    await session.commit()
    await RecoveryTick(worker.observer).apply(
        UUID(project["id"]), row.id, token, 3, github.pulls[100], None, False, True
    )
    await session.refresh(run)
    assert run.state == "failed"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 0


@pytest.mark.parametrize("action", ["pause", "revoke"])
async def test_control_wins_after_remote_read_before_activation(client, setup_work, session, monkeypatch, action):
    project, _, worker, plan, item, run = await terminal(client, setup_work, session)
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    original = RecoveryTick.apply

    async def controlled(self, *args, **kwargs):
        await control(client, project, await get(client, project, plan), action)
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(RecoveryTick, "apply", controlled)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert (await client.get(root + "/recoveries")).json()["items"][0]["state"] == "refused"
    await session.refresh(run)
    assert run.state == "failed"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 0


async def test_three_item_chain_baseline_preserves_success_and_original_dependencies(client, setup_work, session):
    project, github, worker, _ = setup_work
    data = spec()
    data["items"].append(dict(key="c", title="Finish", description="Finish", acceptance="Pass", depends_on=["b"]))
    plan = await create(client, project, data)
    await worker.advance_project(UUID(project["id"]))
    github.merge(100)
    github.refs.pop("main")
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    failed = await get(client, project, plan)
    first, second, _third = failed["items"]
    assert first["state"] == "succeeded" and second["state"] == "preparation_failed"
    # Disabled baseline: ticks alone never recover the failed second Item.
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    baseline = await get(client, project, plan)
    assert baseline["items"][1]["state"] == "preparation_failed"
    assert await session.scalar(select(func.count()).select_from(PipelineRun)) == 1
    github.refs["main"] = "c" * 40
    root = endpoint(project, failed, second)
    assert (await client.post(root + "/recover", json=command(failed, second))).status_code == 200
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    recovered = await get(client, project, plan)
    assert recovered["items"][0] == first
    assert recovered["items"][1]["id"] == second["id"] and recovered["items"][1]["state"] == "running"
    assert recovered["items"][2]["state"] == "waiting"
    assert await session.scalar(select(func.count()).select_from(PipelineRun)) == 2
    github.merge(101)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert (await get(client, project, plan))["items"][2]["state"] == "running"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 0


async def test_capacity_hold_releases_without_reserving_or_losing_identity(client, setup_work, session):
    from app.features.project_management.projects.models import Project

    project, _, worker, plan, item, _run = await terminal(client, setup_work, session)
    project_row = await session.get(Project, UUID(project["id"]))
    project_row.automation = {**project_row.automation, "max_in_flight_runs": 0}
    await session.commit()
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    held = (await client.get(root + "/recoveries")).json()["items"][0]
    assert held["state"] == "awaiting-admission"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 0
    project_row.automation = {**project_row.automation, "max_in_flight_runs": 1}
    await session.commit()
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    resumed = (await client.get(root + "/recoveries")).json()["items"][0]
    assert resumed["id"] == held["id"] and resumed["state"] == "running"


async def test_history_survives_successful_run_pruning(client, setup_work, session):
    from app.features.execution.tasks.domains.maintenance.history import HistoryRetentionRepository

    project, github, worker, plan, item, run = await terminal(client, setup_work, session)
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    github.merge(100)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    current = await session.get(WorkItem, UUID(item["id"]))
    await session.refresh(run)
    current.completed_at = run.updated_at = utc_now() - timedelta(days=31)
    await session.commit()
    await HistoryRetentionRepository().delete_runs(session, before=utc_now() - timedelta(days=30), now=utc_now())
    await session.commit()
    assert await session.get(PipelineRun, run.id, populate_existing=True) is None
    record = (await client.get(root + "/recoveries")).json()["items"][0]
    assert record["state"] == "completed" and record["prior_outcome"]["pipeline_run_id"] == str(run.id)


@pytest.mark.parametrize("fence", ["run_revision", "item_lease", "run_lease"])
async def test_preflight_revision_and_live_leases_refuse_without_history(client, setup_work, session, fence):
    project, _, _, plan, item, run = await terminal(client, setup_work, session)
    data = command(plan, item)
    if fence == "run_revision":
        data["expected_run_revision"] += 1
    elif fence == "item_lease":
        current = await session.get(WorkItem, UUID(item["id"]))
        current.lease_token, current.lease_expires_at = uuid4(), utc_now() + timedelta(minutes=1)
    else:
        run.lease_token, run.lease_expires_at = uuid4(), utc_now() + timedelta(minutes=1)
    await session.commit()
    response = await client.post(endpoint(project, plan, item) + "/recover", json=data)
    assert response.status_code == 409
    assert await session.scalar(select(func.count()).select_from(WorkItemRecovery)) == 0


@pytest.mark.parametrize("hold", ["schedule", "project_disabled", "catalog_quota"])
async def test_recovery_uses_schedule_enabled_project_and_catalog_holds(client, setup_work, session, hold):
    from app.features.ai_catalogs.models import AICatalog
    from app.features.project_management.projects.models import Project
    from app.features.project_management.work_plans.models import WorkPlan

    project, _, worker, plan, item, run = await terminal(client, setup_work, session)
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    if hold == "schedule":
        saved = await session.get(WorkPlan, UUID(plan["id"]))
        saved.scheduled_at = utc_now() + timedelta(hours=1)
    elif hold == "project_disabled":
        saved = await session.get(Project, UUID(project["id"]))
        saved.enabled = False
    else:
        saved = await session.get(AICatalog, run.ai_catalog_id)
        saved.availability_state, saved.available_at = "quota_blocked", utc_now() + timedelta(hours=1)
    await session.commit()
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    record = (await client.get(root + "/recoveries")).json()["items"][0]
    assert record["state"] == "awaiting-admission"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 0
