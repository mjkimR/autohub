"""Project-serialized replacement commands with immutable replay receipts."""

from typing import Annotated

from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans import replacement_repo as repo
from app.features.project_management.work_plans import replacement_service as service
from app.features.project_management.work_plans.activity import record_change, snapshot
from app.features.project_management.work_plans.models import ItemDependency, WorkItem, WorkPlan
from app.features.project_management.work_plans.replacement_models import (
    ReplacementAcceptance,
    ReplacementEvent,
    ReplacementLink,
    ReplacementReceipt,
)
from app.features.project_management.work_plans.replacement_schemas import ReplacementRead
from app.features.project_management.work_plans.services import WorkPlanService
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends


class ReplacementUseCase:
    def __init__(self, plans: Annotated[WorkPlanService, Depends()]):
        self.plans = plans

    async def subject(self, session, project_id, plan_id, item_id):
        plan = await self.plans.get(session, project_id, plan_id)
        item = await session.get(WorkItem, item_id)
        if item is None or item.plan_id != plan.id:
            raise ProjectError(404, "Work Item not found")
        return plan, item

    async def read(
        self, session, plan, item, candidate=None, result=None, offset=0, limit=10, event_link_id=None, event_offset=0
    ):
        row = await service.evidence(session, item.id)
        links = []
        rows, total = await repo.links(session, item.id, offset, limit)
        for link in rows:
            current_offset = event_offset if link.id == event_link_id else 0
            events, event_total = await repo.events(session, link.id, current_offset)
            accepts = await repo.acceptances(session, link.id, [e.acceptance_id for e in events if e.acceptance_id])
            replacement = await session.get(WorkItem, link.replacement_item_id)
            replacement_plan = await session.get(WorkPlan, link.replacement_plan_id)
            links.append(
                dict(
                    id=str(link.id),
                    active=link.active,
                    snapshot=link.snapshot,
                    current_replacement=service.facts(replacement_plan, replacement),
                    event_offset=current_offset,
                    event_total_count=event_total,
                    actor=link.actor,
                    reason=link.reason,
                    acceptances=[
                        dict(
                            id=str(a.id),
                            dependent_item_id=str(a.dependent_item_id),
                            active=a.active,
                            consumed=a.consumed,
                            snapshot=a.snapshot,
                            actor=a.actor,
                            reason=a.reason,
                        )
                        for a in accepts
                    ],
                    events=[
                        dict(
                            id=str(e.id),
                            acceptance_id=str(e.acceptance_id) if e.acceptance_id else None,
                            kind=e.kind,
                            actor=e.actor,
                            reason=e.reason,
                            revision=e.revision,
                            evidence=e.evidence,
                            created_at=e.created_at.isoformat(),
                        )
                        for e in events
                    ],
                )
            )
        return ReplacementRead.model_validate(
            dict(
                original=service.facts(plan, item),
                candidate=candidate,
                evidence_revision=row.revision if row else 0,
                links=links,
                result=result,
                history_offset=offset,
                history_total_count=total,
                history_limit=limit,
            )
        )

    async def get(
        self,
        project_id,
        plan_id,
        item_id,
        replacement_item_id=None,
        offset=0,
        limit=10,
        event_link_id=None,
        event_offset=0,
    ):
        async with AsyncTransaction() as session:
            await self.plans.projects.get(session, project_id, lock=True)
            plan, item = await self.subject(session, project_id, plan_id, item_id)
            candidate = None
            if replacement_item_id:
                other = await session.get(WorkItem, replacement_item_id)
                other_plan = await session.get(WorkPlan, other.plan_id) if other else None
                if not other or not other_plan or other_plan.project_id != project_id:
                    raise ProjectError(404, "Replacement Work Item not found")
                candidate = service.facts(other_plan, other)
            return await self.read(
                session,
                plan,
                item,
                candidate,
                offset=offset,
                limit=limit,
                event_link_id=event_link_id,
                event_offset=event_offset,
            )

    async def mutate(self, project_id, plan_id, item_id, operation, data, actor, link_id=None):
        async with AsyncTransaction() as session:
            project = await self.plans.projects.get(session, project_id, lock=True)
            plan, item = await self.subject(session, project_id, plan_id, item_id)
            digest = request_digest(
                dict(
                    plan_id=str(plan_id),
                    item_id=str(item_id),
                    link_id=str(link_id) if link_id else None,
                    actor=actor,
                    command=data.model_dump(mode="json"),
                )
            )
            prior = await repo.receipt(session, project_id, operation, data.request_id)
            if prior:
                if prior.digest != digest:
                    current = await service.evidence(session, item_id)
                    service.conflict(
                        "Request identity used for another payload or actor", current.revision if current else 0
                    )
                return await self.read(session, plan, item, result=prior.result)
            link = await session.get(ReplacementLink, link_id) if link_id else None
            if operation != "link" and (
                link is None or link.original_item_id != item_id or link.project_id != project_id
            ):
                raise ProjectError(404, "Replacement link not found")
            if operation == "link":
                replacement_id = data.replacement_item_id
            else:
                assert link is not None
                replacement_id = link.replacement_item_id
            replacement = await session.get(WorkItem, replacement_id)
            other_plan = await session.get(WorkPlan, replacement.plan_id) if replacement else None
            if replacement is None or other_plan is None or other_plan.project_id != project_id:
                raise ProjectError(404, "Replacement Work Item not found")
            for pid in sorted({plan.id, other_plan.id}, key=str):
                await session.get(WorkPlan, pid, with_for_update=True, populate_existing=True)
            for rid in sorted({r for r in (item.pipeline_run_id, replacement.pipeline_run_id) if r}, key=str):
                await session.get(PipelineRun, rid, with_for_update=True, populate_existing=True)
            for iid in sorted({item.id, replacement.id}, key=str):
                await session.get(WorkItem, iid, with_for_update=True, populate_existing=True)
            state = await service.evidence(session, item_id, create=True)
            assert state is not None
            if (
                plan.revision != data.expected_original_revision
                or other_plan.revision != data.expected_replacement_revision
                or state.revision != data.expected_evidence_revision
            ):
                service.conflict("Revision changed; reload evidence before confirming", state.revision)
            service.same_binding(project, plan, other_plan, state.revision)
            before = await snapshot(session, plan)
            if operation == "link":
                await service.eligible_original(session, item, state.revision)
                if plan.id == other_plan.id:
                    service.conflict("Replacement must be in another Work Plan", state.revision)
                historical = await repo.endpoint_links(session, [item.id, replacement.id])
                if any(
                    r.replacement_item_id in (item.id, replacement.id)
                    or r.original_item_id == replacement.id
                    or (r.original_item_id == item.id and r.active)
                    for r in historical
                ):
                    service.conflict(
                        "Retained endpoint role, replacement reuse or active link conflicts", state.revision
                    )
                link = ReplacementLink(
                    project_id=project_id,
                    original_plan_id=plan.id,
                    original_item_id=item.id,
                    replacement_plan_id=other_plan.id,
                    replacement_item_id=replacement.id,
                    snapshot=dict(
                        original=service.facts(plan, item), replacement=service.facts(other_plan, replacement)
                    ),
                    actor=actor,
                    reason=data.reason,
                )
                session.add(link)
                await session.flush()
                acceptance = None
            else:
                assert link is not None
                if not link.active:
                    service.conflict("Link withdrawn", state.revision)
                acceptance = None
                if operation == "accept":
                    await service.eligible_original(session, item, state.revision)
                    original_facts, replacement_facts = (
                        service.facts(plan, item),
                        service.facts(other_plan, replacement),
                    )
                    if (
                        original_facts["digest"] != link.snapshot["original"]["digest"]
                        or replacement_facts["digest"] != link.snapshot["replacement"]["digest"]
                    ):
                        service.conflict("Endpoint specification changed", state.revision)
                    merge = await service.confirmed_merge(session, other_plan, replacement, state.revision)
                    if (
                        data.original_digest != original_facts["digest"]
                        or data.replacement_digest != replacement_facts["digest"]
                        or data.merge_sha != merge["merge_sha"]
                        or str(data.execution_id) != merge["execution_id"]
                    ):
                        service.conflict("Displayed specification or merge identity changed", state.revision)
                    edge = await session.get(ItemDependency, (data.dependent_item_id, item.id))
                    if edge is None or edge.plan_id != plan.id:
                        service.conflict("Existing local dependency edge not found", state.revision)
                    existing = list(await repo.acceptances(session, link.id))
                    if any(a.active and a.dependent_item_id == data.dependent_item_id for a in existing):
                        service.conflict("Dependency already has live acceptance", state.revision)
                    acceptance = ReplacementAcceptance(
                        link_id=link.id,
                        plan_id=plan.id,
                        dependent_item_id=data.dependent_item_id,
                        original_item_id=item.id,
                        snapshot=dict(original=original_facts, replacement=merge),
                        actor=actor,
                        reason=data.reason,
                    )
                    session.add(acceptance)
                    await session.flush()
                elif operation == "withdraw":
                    acceptances = await repo.acceptances(session, link.id)
                    if data.acceptance_id:
                        acceptance = next((a for a in acceptances if a.id == data.acceptance_id), None)
                        if acceptance is None:
                            raise ProjectError(404, "Acceptance not found")
                        if acceptance.consumed or not acceptance.active:
                            service.conflict("Acceptance consumed or withdrawn", state.revision)
                        acceptance.active = False
                    else:
                        if any(a.consumed for a in acceptances):
                            service.conflict("Link has consumed acceptance", state.revision)
                        link.active = False
                        for a in acceptances:
                            a.active = False
            assert link is not None
            state.revision += 1
            plan.revision += 1
            result = dict(
                operation=operation,
                request_id=str(data.request_id),
                link_id=str(link.id),
                acceptance_id=str(acceptance.id) if acceptance else None,
                original_revision=plan.revision,
                evidence_revision=state.revision,
            )
            session.add(
                ReplacementEvent(
                    link_id=link.id,
                    acceptance_id=acceptance.id if acceptance else None,
                    kind=operation,
                    actor=actor,
                    reason=data.reason,
                    revision=state.revision,
                    evidence=result,
                )
            )
            session.add(
                ReplacementReceipt(
                    project_id=project_id,
                    original_item_id=item.id,
                    operation=operation,
                    request_id=data.request_id,
                    digest=digest,
                    result=result,
                )
            )
            await record_change(session, plan, before, "replacement", actor, data.reason)
            await session.flush()
            return await self.read(session, plan, item, result=result)
