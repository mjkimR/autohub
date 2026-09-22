"""Build outbound snapshots from local facts only. Never read GitHub issue content."""

from uuid import UUID

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.work_plans.models import ItemDependency, PlanDependency, WorkIssueMirror, WorkPlan
from app.features.project_management.work_plans.repos import WorkPlanRepository
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

NOTICE = "AutoHub-managed record. Changes to this issue do not change execution, dependencies, or completion."


async def refresh_mirrors(session: AsyncSession, plan: WorkPlan) -> None:
    items = await WorkPlanRepository().items(session, plan.id)
    plan_deps = list(
        await session.scalars(select(PlanDependency.depends_on_id).where(PlanDependency.plan_id == plan.id))
    )
    mirrors = {
        row.entity_id: row
        for row in await session.scalars(
            select(WorkIssueMirror).where(
                or_(WorkIssueMirror.plan_id == plan.id, WorkIssueMirror.entity_id.in_(plan_deps)),
            )
        )
    }
    names = {item.id: item.key + ": " + item.title for item in items}
    names.update(
        {row.id: row.title for row in await session.scalars(select(WorkPlan).where(WorkPlan.id.in_(plan_deps)))}
    )
    edges = list(await session.scalars(select(ItemDependency).where(ItemDependency.plan_id == plan.id)))

    def link(entity_id: UUID, label: str) -> str:
        row = mirrors.get(entity_id)
        return f"[{label}]({row.issue_url})" if row and row.issue_url else label

    for entity in [plan, *items]:
        is_plan = isinstance(entity, WorkPlan)
        parents = plan_deps if is_plan else [edge.depends_on_id for edge in edges if edge.item_id == entity.id]
        dependencies = ", ".join(link(id, names.get(id, str(id))) for id in parents) or "None"
        body = f"{NOTICE}\n\nAutoHub plan: `{plan.id}`\n\n{entity.description}\n\n"
        if not is_plan:
            body += f"## Acceptance criteria\n\n{entity.acceptance}\n\n"
            body += f"Plan: {link(plan.id, plan.title)}\n\n"
            if entity.pull_url:
                body += f"Implementation: {entity.pull_url}\n\n"
            if entity.merge_sha:
                body += f"Merge commit: `{entity.merge_sha}`\n\n"
        else:
            body += (
                "## Work items\n\n"
                + "\n".join(f"- {link(item.id, item.key + ': ' + item.title)} — {item.state}" for item in items)
                + "\n\n"
            )
        state = entity.state
        detail = None if is_plan else entity.detail
        body += f"Depends on: {dependencies}\n\nStatus: **{state}**\n"
        if detail:
            body += f"\n{detail}\n"
        row = mirrors.get(entity.id)
        history = list((row.desired if row else {}).get("history", []))
        if not history or history[-1]["state"] != state:
            history.append({"state": state, "at": get_current_utc_time().isoformat()})
        history = history[-100:]
        body += "\n## History\n\n" + "\n".join(f"- {event['at']}: {event['state']}" for event in history)
        body += f"\n\n<!-- autohub-work:{entity.id} -->"
        desired = {
            "title": f"[AutoHub {'Plan' if is_plan else entity.key}] {entity.title}"[:256],
            "body": body.replace("@", "@\u200b"),
            "state": "closed" if state in ("succeeded", "completed", "revoked", "canceled") else "open",
            "state_reason": "completed" if state in ("succeeded", "completed") else "not_planned",
            "history": history,
            "parent": None if is_plan else str(plan.id),
            "dependencies": [str(id) for id in parents],
        }
        digest = request_digest(desired)
        if row is None:
            row = WorkIssueMirror(plan_id=plan.id, entity_id=entity.id, desired=desired, digest=digest)
            session.add(row)
            mirrors[entity.id] = row
        elif row.digest != digest:
            row.desired, row.digest = desired, digest
    await session.flush()
