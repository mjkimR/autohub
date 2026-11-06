"""Exact local edge satisfaction. Caller holds Project and Plan admission ownership."""

from app.features.project_management.work_plans import replacement_service as service
from app.features.project_management.work_plans.models import ItemDependency, WorkItem, WorkPlan
from app.features.project_management.work_plans.replacement_models import (
    ReplacementAcceptance,
    ReplacementEvent,
    ReplacementLink,
)
from sqlalchemy import select


async def consume(session, plan, dependent):
    edges = list(await session.scalars(select(ItemDependency).where(ItemDependency.item_id == dependent.id)))
    accepted = []
    for edge in edges:
        original = await session.get(WorkItem, edge.depends_on_id)
        if original and original.state == "succeeded":
            continue
        acceptance = await session.scalar(
            select(ReplacementAcceptance)
            .join(ReplacementLink)
            .where(
                ReplacementAcceptance.dependent_item_id == dependent.id,
                ReplacementAcceptance.original_item_id == edge.depends_on_id,
                ReplacementAcceptance.active.is_(True),
                ReplacementLink.active.is_(True),
            )
        )
        if acceptance is None or original is None:
            return False
        link = await session.get(ReplacementLink, acceptance.link_id)
        replacement = await session.get(WorkItem, link.replacement_item_id)
        replacement_plan = await session.get(WorkPlan, link.replacement_plan_id)
        if (
            replacement is None
            or replacement_plan is None
            or acceptance.plan_id != plan.id
            or link.project_id != plan.project_id
            or replacement_plan.project_id != plan.project_id
            or (plan.repository, plan.connector_id, plan.base_branch)
            != (replacement_plan.repository, replacement_plan.connector_id, replacement_plan.base_branch)
            or service.item_digest(original) != acceptance.snapshot["original"]["digest"]
            or service.item_digest(replacement) != acceptance.snapshot["replacement"]["digest"]
            or replacement.state != "succeeded"
            or replacement.merge_sha != acceptance.snapshot["replacement"]["merge_sha"]
            or str(replacement.execution_id) != acceptance.snapshot["replacement"]["execution_id"]
        ):
            return False
        accepted.append(acceptance)
    changed = False
    before = None
    for acceptance in accepted:
        if not acceptance.consumed:
            from app.features.project_management.work_plans.activity import snapshot

            if before is None:
                before = await snapshot(session, plan)
            changed = True
            acceptance.consumed = True
            state = await service.evidence(session, acceptance.original_item_id, create=True)
            assert state is not None
            state.revision += 1
            session.add(
                ReplacementEvent(
                    link_id=acceptance.link_id,
                    acceptance_id=acceptance.id,
                    kind="consumed",
                    actor="system:work-execution",
                    reason="Dependency admitted",
                    revision=state.revision,
                    evidence={"dependent_item_id": str(dependent.id), "acceptance_id": str(acceptance.id)},
                )
            )
    if changed:
        assert before is not None
        from app.features.project_management.work_plans.activity import record_change

        plan.revision += 1
        await record_change(
            session, plan, before, "replacement", "system:work-execution", "Consumed exact replacement edge"
        )
    return True
