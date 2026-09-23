"""Resolve referenced IDs to readable names so agents need no follow-up lookups."""

from uuid import UUID

from app.mcp.dependencies import Dependencies, connector_reader
from app_layer_base.base.repos.query_options import ListQueryOptions


async def catalog_keys(deps: Dependencies) -> dict[UUID, str]:
    return {row.id: row.key for row in (await deps.catalogs.list()).items}


async def connector_names() -> dict[UUID, str]:
    result = await connector_reader().execute(ListQueryOptions(offset=0, limit=100))
    return {row.id: row.name for row in result.items}
