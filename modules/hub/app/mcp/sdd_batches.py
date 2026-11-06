from uuid import UUID

from app.features.project_management.sdd.batch_schemas import ControlBatch
from app.features.project_management.sdd.batch_usecases import SddBatchUseCase
from app.features.project_management.sdd.usecases import SddUseCase
from app.mcp.auth import authenticated_context
from app.mcp.contracts import ProjectId
from app.mcp.delivery_views import BatchList, BatchView, batch_summary, batch_view
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app_mcp import ToolRegistry


class BatchId(ProjectId):
    batch_id: UUID


class BatchControl(BatchId):
    control: ControlBatch


def register_batches(registry: ToolRegistry, deps: Dependencies):
    owner = SddBatchUseCase(deps.project_service, SddUseCase(deps.project_service, deps.observer, deps.runs))

    async def listing(args: ProjectId) -> BatchList:
        return BatchList(items=[batch_summary(row) for row in (await owner.lists(args.project_id))[:50]])

    async def get(args: BatchId) -> BatchView:
        return batch_view(await owner.get(args.project_id, args.batch_id))

    async def control(args: BatchControl) -> BatchView:
        actor = f"machine:{(await authenticated_context()).subject}"
        return batch_view(await owner.control(args.project_id, args.batch_id, args.control, actor))

    register(
        registry,
        "sdd_batches_list",
        "Read latest at most 50 batch summaries; this is a history window, not complete history.",
        ProjectId,
        BatchList,
        listing,
    )
    register(
        registry,
        "sdd_batches_get",
        "Read exact batch status and latest claim evidence per member; omitted history is disclosed.",
        BatchId,
        BatchView,
        get,
    )
    register(
        registry,
        "sdd_batches_control",
        "Pause/resume/stop future admission only; admitted work keeps its owner. Reuse request_id and identical payload after response loss; supply reviewed revision.",
        BatchControl,
        BatchView,
        control,
        write=True,
    )
