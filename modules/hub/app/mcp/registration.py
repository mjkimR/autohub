"""Bind typed application handlers to the shared policy registry."""

import re
from collections.abc import Awaitable, Callable
from typing import cast

from app.auth import MCP_OPS, MCP_READ, MCP_WRITE
from app_mcp import ToolContext, ToolDefinition, ToolRegistry, ToolResult, ToolRisk
from pydantic import BaseModel


def register[InputModel: BaseModel, OutputModel: BaseModel](
    registry: ToolRegistry,
    name: str,
    description: str,
    input_model: type[InputModel],
    output_model: type[OutputModel],
    handler: Callable[[InputModel], Awaitable[OutputModel]],
    *,
    write: bool = False,
    ops: bool = False,
) -> None:
    if len(name) > 64 or not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", name):
        raise ValueError("MCP tool names must be lowercase snake_case and at most 64 characters")

    async def invoke(_: ToolContext, arguments: BaseModel) -> ToolResult:
        return ToolResult.success(await handler(cast(InputModel, arguments)))

    registry.register(
        ToolDefinition(
            name=name,
            description=description,
            handler=invoke,
            input_model=input_model,
            output_model=output_model,
            required_scopes=frozenset({MCP_OPS if ops else MCP_WRITE if write else MCP_READ}),
            risk=ToolRisk.WRITE if write else ToolRisk.READ,
        )
    )
