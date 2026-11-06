from uuid import UUID

from app.features.project_management.work_plans.replacement_schemas import (
    ReplacementAcceptCommand,
    ReplacementLinkCommand,
    ReplacementWithdrawCommand,
)
from app.features.project_management.work_plans.replacement_usecase import ReplacementUseCase
from app.mcp.auth import authenticated_context
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app.mcp.replacement_views import ReplacementView, replacement_view
from app.mcp.work_item_recovery import ItemId, work_owner
from app_mcp import ToolRegistry
from pydantic import Field


class Replacements(ItemId):
    replacement_item_id: UUID | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=10, ge=1, le=100)
    event_link_id: UUID | None = None
    event_offset: int = Field(default=0, ge=0)


class Link(ItemId):
    command: ReplacementLinkCommand


class Accept(ItemId):
    link_id: UUID
    command: ReplacementAcceptCommand


class Withdraw(ItemId):
    link_id: UUID
    command: ReplacementWithdrawCommand


def register_replacements(registry: ToolRegistry, deps: Dependencies):
    owner = ReplacementUseCase(work_owner(deps).service)

    async def listing(args: Replacements) -> ReplacementView:
        return replacement_view(
            await owner.get(
                args.project_id,
                args.plan_id,
                args.item_id,
                args.replacement_item_id,
                args.offset,
                min(args.limit, 99),
                args.event_link_id,
                args.event_offset,
            )
        )

    async def mutate(args, operation):
        actor = f"machine:{(await authenticated_context()).subject}"
        return replacement_view(
            await owner.mutate(
                args.project_id,
                args.plan_id,
                args.item_id,
                operation,
                args.command,
                actor,
                getattr(args, "link_id", None),
            )
        )

    async def link(args: Link) -> ReplacementView:
        return await mutate(args, "link")

    async def accept(args: Accept) -> ReplacementView:
        return await mutate(args, "accept")

    async def withdraw(args: Withdraw) -> ReplacementView:
        return await mutate(args, "withdraw")

    register(
        registry,
        "work_items_replacements",
        "Read bounded replacement evidence and exact active/consumed state; no task text or raw snapshots.",
        Replacements,
        ReplacementView,
        listing,
    )
    register(
        registry,
        "work_items_replacement_link",
        "Link distinct replacement work without releasing dependencies. Reuse request_id with identical command after response loss.",
        Link,
        ReplacementView,
        link,
        write=True,
    )
    register(
        registry,
        "work_items_replacement_accept",
        "Accept reviewed merge evidence for one existing local dependency edge; not PR/native approval. Reuse request_id and unchanged payload on retry.",
        Accept,
        ReplacementView,
        accept,
        write=True,
    )
    register(
        registry,
        "work_items_replacement_withdraw",
        "Withdraw only unconsumed replacement evidence; no cancellation or merge reversal. Reuse request_id and unchanged payload on retry.",
        Withdraw,
        ReplacementView,
        withdraw,
        write=True,
    )
