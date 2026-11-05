"""Recovery persistence and preflight. Caller owns the transaction and parent locks."""

from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.models import Project
from app.features.project_management.work_plans.activity import record_change, snapshot
from app.features.project_management.work_plans.models import WorkItemRecovery, WorkItemRecoveryEvent
from app.features.project_management.work_plans.recovery_schemas import (
    RecoveryEligibility,
    RecoveryEventRead,
    WorkItemRecover,
    WorkItemRecoveryList,
    WorkItemRecoveryRead,
)
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import func, select

PENDING = ("accepted", "reconciling", "awaiting-admission")


async def event(session, recovery, kind, detail, evidence=None):
    if kind == "refused" and not evidence:
        codes = {
            "Plan": "PLAN_CHANGED",
            "Run": "RUN_CHANGED",
            "PR identity": "PR_IDENTITY_CHANGED",
            "Original PR is closed": "PR_CLOSED",
            "Another active Run": "ACTIVE_RUN_CONFLICT",
            "Repository connection": "REPOSITORY_CHANGED",
            "Automatic budget exhausted": "RECOVERY_BUDGET_EXHAUSTED",
        }
        code = next((code for prefix, code in codes.items() if detail.startswith(prefix)), "RECOVERY_REFUSED")
        evidence = {"reason": code}
    if recovery.state != kind or recovery.detail != detail or kind == "accepted":
        sequence = (
            await session.scalar(
                select(func.max(WorkItemRecoveryEvent.sequence)).where(WorkItemRecoveryEvent.recovery_id == recovery.id)
            )
            or 0
        ) + 1
        session.add(
            WorkItemRecoveryEvent(
                recovery_id=recovery.id, sequence=sequence, kind=kind, detail=detail, evidence=evidence or {}
            )
        )
    recovery.state, recovery.detail = kind, detail
    await session.flush()


async def pending(session, item_id):
    return await session.scalar(
        select(WorkItemRecovery).where(WorkItemRecovery.item_id == item_id, WorkItemRecovery.state.in_(PENDING))
    )


async def eligibility(session, plan, item, *, ignore_pending=False):
    run = await session.get(PipelineRun, item.pipeline_run_id) if item.pipeline_run_id else None
    recovery = None if ignore_pending else await pending(session, item.id)
    project = await session.get(Project, plan.project_id)
    reason, action = "eligible", "Review unchanged work and confirm retry"
    now = get_current_utc_time()
    if recovery:
        reason, action = "recovery_pending", "Refresh recovery status"
    elif plan.state != "active":
        reason, action = (
            "plan_" + plan.state,
            "Resume the Plan explicitly" if plan.state == "paused" else "Inspect Plan",
        )
    elif project is None or project.project_type == "sdd":
        reason, action = "native_project", "Use the bound repository spec"
    elif item.state not in ("preparation_failed", "failed", "canceled"):
        reason, action = "item_" + item.state, "Inspect current execution"
    elif item.lease_expires_at and as_utc(item.lease_expires_at) > now:
        reason, action = "item_leased", "Wait for reconciliation and refresh"
    elif item.pipeline_run_id and run is None:
        reason, action = "missing_run", "Inspect missing execution"
    elif run and run.state not in ("failed", "canceled"):
        reason, action = "run_" + run.state, "Open existing Run controls"
    elif run and run.lease_expires_at and as_utc(run.lease_expires_at) > now:
        reason, action = "run_leased", "Wait for the prior owner to stop"
    elif run and (
        run.sdd_snapshot
        or run.github_repository != plan.repository
        or run.github_connector_id != plan.connector_id
        or run.branch != item.branch
        or run.pull_snapshot.get("base_ref") != plan.base_branch
    ):
        reason, action = "execution_identity", "Inspect original execution binding"
    elif item.state != "preparation_failed" and run is None:
        reason, action = "missing_run", "Inspect missing execution"
    return RecoveryEligibility(
        eligible=reason == "eligible",
        reason=reason,
        next_action=action,
        run_revision=run.revision if run else None,
        pending_state=recovery.state if recovery else None,
        pending_detail=recovery.detail if recovery else None,
    )


async def read_recovery(session, row):
    events = await session.scalars(
        select(WorkItemRecoveryEvent)
        .where(WorkItemRecoveryEvent.recovery_id == row.id)
        .order_by(WorkItemRecoveryEvent.sequence)
    )
    events = list(events)
    return WorkItemRecoveryRead.model_validate(row).model_copy(
        update={
            "events": [RecoveryEventRead.model_validate(e) for e in events],
            "refusal_reason": events[-1].evidence.get("reason") if events and row.state == "refused" else None,
        }
    )


async def history(session, item_id, offset, limit):
    query = select(WorkItemRecovery).where(WorkItemRecovery.item_id == item_id)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.scalars(
        query.order_by(WorkItemRecovery.created_at.desc(), WorkItemRecovery.id).offset(offset).limit(limit)
    )
    return WorkItemRecoveryList(items=[await read_recovery(session, r) for r in rows], total_count=total or 0)


async def accept(session, plan, item, run, data: WorkItemRecover, actor: str):
    digest = request_digest({"item_id": str(item.id), "actor": actor, "command": data.model_dump(mode="json")})
    existing = await session.scalar(
        select(WorkItemRecovery).where(
            WorkItemRecovery.project_id == plan.project_id, WorkItemRecovery.request_id == data.request_id
        )
    )
    if existing:
        if existing.request_digest != digest:
            raise ProjectError(409, "Recovery identity was used for different input", code="RECOVERY_IDENTITY_CONFLICT")
        return existing
    if plan.revision != data.expected_revision or (run and run.revision != data.expected_run_revision):
        raise ProjectError(409, "Reload Plan and Run before recovering", code="RECOVERY_STALE")
    allowed = await eligibility(session, plan, item)
    if not allowed.eligible:
        raise ProjectError(409, allowed.next_action, code=allowed.reason)
    before = await snapshot(session, plan)
    prior: dict = {
        k: str(getattr(item, k)) if getattr(item, k) is not None else None
        for k in (
            "state",
            "detail",
            "branch",
            "base_sha",
            "pull_number",
            "pull_url",
            "merge_sha",
            "pipeline_run_id",
            "execution_id",
            "started_at",
            "completed_at",
        )
    }
    prior["repository"] = plan.repository
    prior["target_branch"] = plan.base_branch
    prior["run"] = (
        {
            "state": run.state,
            "revision": run.revision,
            "epoch": run.epoch,
            "pause_reason": run.pause_reason,
            "head_sha": run.pull_snapshot.get("head_sha"),
        }
        if run
        else None
    )
    row = WorkItemRecovery(
        project_id=plan.project_id,
        plan_id=plan.id,
        item_id=item.id,
        request_id=data.request_id,
        request_digest=digest,
        actor=actor,
        reason=data.reason,
        command=data.model_dump(mode="json"),
        prior_outcome=prior,
        accepted_revision=plan.revision + 1,
        accepted_run_revision=run.revision if run else None,
    )
    session.add(row)
    await session.flush()
    await event(session, row, "accepted", "Accepted; checking original execution")
    plan.revision += 1
    await record_change(session, plan, before, "recovery", actor, data.reason)
    return row


async def record_result(session, item):
    if item.state not in ("succeeded", "preparation_failed", "failed", "canceled"):
        return
    row = await session.scalar(
        select(WorkItemRecovery)
        .where(WorkItemRecovery.item_id == item.id, WorkItemRecovery.state == "running")
        .order_by(WorkItemRecovery.created_at.desc())
        .limit(1)
    )
    if row:
        await event(
            session,
            row,
            "completed" if item.state == "succeeded" else "failed",
            item.detail or item.state,
            {"item_state": item.state, "merge_sha": item.merge_sha},
        )
