"""Authenticate the mounted transport independently of REST dependencies."""

from urllib.parse import urlsplit

from app.auth import MCP_SCOPES
from app_mcp import ToolContext
from app_prebuilt_auth.api_key.database import get_api_key_session_maker
from app_prebuilt_auth.api_key.exceptions import InvalidApiKey
from app_prebuilt_auth.api_key.usecases import ApiKeyUseCase
from fastmcp.server.dependencies import get_http_request
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


async def authenticated_context() -> ToolContext:
    return get_http_request().state.mcp_context


class MCPAuthentication:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        origin = headers.get("origin")
        if origin:
            try:
                parsed = urlsplit(origin)
                allowed = parsed.scheme in {"http", "https"} and parsed.netloc == headers.get("host")
            except ValueError:
                allowed = False
            if not allowed:
                await JSONResponse({"detail": "Origin is not allowed"}, status_code=403)(scope, receive, send)
                return
        authorization = headers.get("authorization", "")
        scheme, _, credential = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credential.strip():
            await self._unauthorized(scope, receive, send)
            return
        try:
            keys = ApiKeyUseCase(await get_api_key_session_maker(), MCP_SCOPES)
            principal = await keys.authenticate(credential.strip())
        except InvalidApiKey:
            await self._unauthorized(scope, receive, send)
            return
        if not principal.scopes & MCP_SCOPES:
            await JSONResponse({"detail": "An MCP scope is required"}, status_code=403)(scope, receive, send)
            return
        scope.setdefault("state", {})["mcp_context"] = ToolContext(
            subject=str(principal.machine_id), scopes=principal.scopes
        )
        await self.app(scope, receive, send)

    @staticmethod
    async def _unauthorized(scope: Scope, receive: Receive, send: Send) -> None:
        await JSONResponse(
            {"detail": "A valid MCP machine key is required"},
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="autohub-mcp"'},
        )(scope, receive, send)
