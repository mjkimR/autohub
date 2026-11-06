from uuid import UUID

from app.features.project_management.work_plans.kick import WorkPlanKick
from app.features.project_management.work_plans.recovery_schemas import WorkItemRecover
from app.features.project_management.work_plans.repos import WorkPlanRepository
from app.features.project_management.work_plans.services import WorkPlanService
from app.features.project_management.work_plans.usecases import WorkPlanUseCase
from app.mcp.auth import authenticated_context
from app.mcp.contracts import Page, ProjectId
from app.mcp.delivery_views import RecoveredItem, RecoveryPage, RecoveryResult, recovery_view
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app_mcp import ToolRegistry


class ItemId(ProjectId):
    plan_id: UUID
    item_id: UUID


class Recoveries(ItemId, Page):
    pass


class RecoverItem(ItemId):
    recovery: WorkItemRecover


def work_owner(deps: Dependencies) -> WorkPlanUseCase:
    return WorkPlanUseCase(WorkPlanService(WorkPlanRepository(), deps.project_service), WorkPlanKick(deps.runs))


def register_recovery(registry: ToolRegistry, deps: Dependencies):
    owner = work_owner(deps)

    async def listing(args: Recoveries) -> RecoveryPage:
        row = await owner.recoveries(args.project_id, args.plan_id, args.item_id, args.offset, args.limit)
        return RecoveryPage(items=[recovery_view(item) for item in row.items], total_count=row.total_count)

    async def recover(args: RecoverItem) -> RecoveryResult:
        actor = f"machine:{(await authenticated_context()).subject}"
        row = await owner.recover(args.project_id, args.plan_id, args.item_id, args.recovery, actor)
        return RecoveryResult(recovery=recovery_view(row.recovery), item=RecoveredItem.model_validate(row.item))

    register(
        registry,
        "work_items_recoveries",
        "Read paged retained recovery evidence; no execution or raw command snapshots.",
        Recoveries,
        RecoveryPage,
        listing,
    )
    register(
        registry,
        "work_items_recover",
        "Recover eligible unchanged work through its owner. Reuse request_id with identical payload after response loss; no automatic retry or approval.",
        RecoverItem,
        RecoveryResult,
        recover,
        write=True,
    )
