"""Exact endpoint and merge evidence. No external observation or transaction ownership."""

from typing import NoReturn

from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans import replacement_repo as repo
from app.features.project_management.work_plans.recovery import pending
from app.features.project_management.work_plans.replacement_models import ReplacementEvidence
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import select


def conflict(reason, revision) -> NoReturn:
    raise ProjectError(409, f"{reason}; current evidence revision={revision}", code="REPLACEMENT_CONFLICT")


def item_digest(item):
    return request_digest({k: getattr(item, k) for k in ("key", "title", "description", "acceptance", "attach_branch")})


def facts(plan, item):
    return dict(
        plan_id=str(plan.id),
        item_id=str(item.id),
        key=item.key,
        title=item.title,
        description=item.description,
        acceptance=item.acceptance,
        digest=item_digest(item),
        plan_revision=plan.revision,
        plan_state=plan.state,
        item_state=item.state,
        repository=plan.repository,
        connector_id=str(plan.connector_id),
        target=plan.base_branch,
        branch=item.branch,
        execution_id=str(item.execution_id) if item.execution_id else None,
        pull_number=item.pull_number,
        pull_url=item.pull_url,
        merge_sha=item.merge_sha,
        completed_at=item.completed_at.isoformat() if item.completed_at else None,
    )


async def evidence(session, item_id, *, create=False):
    row = await session.get(ReplacementEvidence, item_id, with_for_update=create)
    if row is None and create:
        row = ReplacementEvidence(item_id=item_id, revision=0)
        session.add(row)
        await session.flush()
    return row


async def eligible_original(session, item, revision):
    now = get_current_utc_time()
    run = await session.get(PipelineRun, item.pipeline_run_id) if item.pipeline_run_id else None
    if (
        item.state not in ("preparation_failed", "failed", "canceled", "revoked")
        or item.merge_sha
        or await pending(session, item.id)
        or (item.lease_expires_at and as_utc(item.lease_expires_at) > now)
        or (
            run
            and (
                run.state not in ("failed", "canceled") or (run.lease_expires_at and as_utc(run.lease_expires_at) > now)
            )
        )
        or (item.pipeline_run_id and run is None)
    ):
        conflict("Original execution is not stopped unsuccessful work", revision)


def same_binding(project, original_plan, replacement_plan, revision):
    current = (project.github_repository, project.github_connector_id)
    original = (original_plan.repository, original_plan.connector_id)
    replacement = (replacement_plan.repository, replacement_plan.connector_id)
    if (
        project.project_type == "sdd"
        or current != original
        or original != replacement
        or original_plan.base_branch != replacement_plan.base_branch
    ):
        conflict("Project, repository, connector or target identity differs", revision)


async def confirmed_merge(session, plan, item, revision):
    f = facts(plan, item)
    if item.state != "succeeded" or not all(
        f[k] for k in ("execution_id", "pull_number", "pull_url", "merge_sha", "completed_at", "branch")
    ):
        conflict("Replacement has no complete retained confirmed merge evidence", revision)
    if item.pipeline_run_id:
        run = await session.get(PipelineRun, item.pipeline_run_id)
        if run is None or (
            run.id != item.execution_id
            or run.project_id != plan.project_id
            or run.github_repository != plan.repository
            or run.github_connector_id != plan.connector_id
            or run.pull_number != item.pull_number
            or run.branch != item.branch
            or run.pull_snapshot.get("base_ref") != plan.base_branch
            or run.sdd_snapshot
        ):
            conflict("Replacement execution identity differs", revision)
    elif item.pipeline_run_retired_at is None:
        conflict("Missing replacement execution without retirement evidence", revision)
    return f


async def guard_edit(session, plan, items, data):
    relations = await repo.endpoint_links(session, [item.id for item in items], active=True)
    if not relations:
        return
    linked_ids = {i for r in relations for i in (r.original_item_id, r.replacement_item_id)}
    writes = {w.key: w for w in data.items}
    for item in items:
        if item.id in linked_ids:
            write = writes.get(item.key)
            if (
                data.base_branch != plan.base_branch
                or write is None
                or any(
                    getattr(write, k) != getattr(item, k)
                    for k in ("title", "description", "acceptance", "attach_branch")
                )
            ):
                current = await evidence(session, item.id)
                conflict(
                    "Withdraw live replacement link before editing its endpoint", current.revision if current else 0
                )
    # Existing edge identities referenced by retained acceptance must remain stable.
    if relations:
        from app.features.project_management.work_plans.replacement_models import ReplacementAcceptance, ReplacementLink

        retained = list(
            await session.scalars(
                select(ReplacementAcceptance)
                .join(ReplacementLink)
                .where(
                    ReplacementAcceptance.plan_id == plan.id,
                    ReplacementAcceptance.active.is_(True),
                    ReplacementLink.active.is_(True),
                )
            )
        )
        ids_to_keys = {item.id: item.key for item in items}
        for acceptance in retained:
            child, parent = ids_to_keys[acceptance.dependent_item_id], ids_to_keys[acceptance.original_item_id]
            if child not in writes or parent not in writes or parent not in writes[child].depends_on:
                conflict("Retained replacement edge cannot be removed", 0)
