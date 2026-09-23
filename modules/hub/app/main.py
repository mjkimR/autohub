# ruff: noqa: E402
from app_layer_base.config_util import load_env

load_env()

import os
from contextlib import asynccontextmanager
from pathlib import Path

from app.access_logging import configure_access_logging
from app.auth import MACHINE_SCOPES, login_caller, login_lockout_listener, require_machine_admin
from app.auth_settings import get_hub_auth_settings
from app.features import tasks
from app.features.project_management.projects.errors import ProjectError
from app.features.scheduling.schedule_configs.system import ensure_maintenance_schedule
from app.mcp.server import create_hub_mcp
from app.router import router
from app_http_client.instance import close_http_client
from app_layer_base.base.exceptions.handler import set_exception_handler
from app_layer_base.core import middlewares
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.core.log import logger
from app_prebuilt_auth.api_key.config import get_api_key_settings
from app_prebuilt_auth.api_key.deps import require_key_admin
from app_prebuilt_auth.api_key.usecases import get_machine_scopes
from app_prebuilt_auth.google.config import get_google_auth_settings
from app_prebuilt_auth.user.config import get_auth_settings
from app_prebuilt_auth.user.deps import get_login_caller, get_login_lockout_listener
from app_prebuilt_auth.user.repos import UserRepository
from app_prebuilt_auth.user.services import UserService
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError
from starlette.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles


def _resolve_ui_dist() -> Path | None:
    custom_path = os.getenv("UI_DIST_PATH")
    if custom_path:
        p = Path(custom_path)
        if p.is_dir() and (p / "index.html").is_file():
            return p
    container_path = Path(__file__).resolve().parent.parent / "ui_dist"
    if container_path.is_dir() and (container_path / "index.html").is_file():
        return container_path
    return None


async def ensure_first_user() -> None:
    """Create the operator's account from the deployment's secrets, and keep its password equal to them.

    A failure is logged, not raised: webhooks and the scheduler must keep working even when nobody can sign in.
    """
    try:
        service = UserService(settings=get_hub_auth_settings(), repo=UserRepository())
        async with AsyncTransaction() as session:
            await service.ensure_first_user(session)
    except IntegrityError:
        # Several workers start at once; another one created the account first.
        pass
    except Exception:
        logger.exception("The first user could not be ensured; nobody can sign in until this is fixed")


def get_lifespan():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting app lifespan")
        tasks.autodiscover()
        get_api_key_settings()
        get_google_auth_settings()
        await ensure_first_user()
        async with AsyncTransaction() as session:
            await ensure_maintenance_schedule(session)
        try:
            yield
        finally:
            await close_http_client()
        logger.info("End of app lifespan")

    return lifespan


def create_app():
    """Create the FastAPI app and include the router."""
    load_env()
    configure_access_logging()
    hub_lifespan = get_lifespan()
    mcp_app = create_hub_mcp()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with hub_lifespan(app), mcp_app.lifespan(app):
            yield

    app = FastAPI(
        title="Auto Hub",
        version="0.1.0",
        lifespan=lifespan,
        swagger_ui_parameters={
            "persistAuthorization": True,
            "docExpansion": "none",
            "filter": True,
        },
    )

    # Others
    middlewares.timeout_middleware.add_middleware(app)
    middlewares.query_counter.add_middleware(app)

    # Security middleware
    middlewares.security_header.add_middleware(app)
    middlewares.cors_middleware.add_middleware(app)

    # Request ID middleware (Last one to ensure all logs have request ID)
    middlewares.request_id_middleware.add_middleware(app)

    app.include_router(router)
    app.dependency_overrides[get_auth_settings] = get_hub_auth_settings
    app.dependency_overrides[require_key_admin] = require_machine_admin
    app.dependency_overrides[get_machine_scopes] = lambda: MACHINE_SCOPES
    app.dependency_overrides[get_login_caller] = login_caller
    app.dependency_overrides[get_login_lockout_listener] = login_lockout_listener

    set_exception_handler(app)

    @app.exception_handler(ProjectError)
    async def project_error_handler(request, exc: ProjectError):
        return JSONResponse(status_code=exc.status, content={"detail": exc.detail})

    @app.api_route("/mcp", methods=["GET", "POST", "DELETE", "OPTIONS"], include_in_schema=False)
    async def mcp_redirect():
        return RedirectResponse("/mcp/", status_code=307)

    app.mount("/mcp", mcp_app)

    ui_dist = _resolve_ui_dist()
    if ui_dist is not None:
        app_dir = ui_dist / "_app"
        if app_dir.is_dir():
            app.mount("/_app", StaticFiles(directory=str(app_dir)), name="spa_app")

        @app.get("/")
        async def root_spa():
            return FileResponse(ui_dist / "index.html")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # Well-known discovery (e.g. OAuth metadata) must not fall back to the SPA shell.
            if full_path.startswith(".well-known/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            target = (ui_dist / full_path).resolve()
            if full_path and target.is_relative_to(ui_dist.resolve()) and target.is_file():
                return FileResponse(target)
            return FileResponse(ui_dist / "index.html")
    else:

        @app.get("/")
        async def root_docs():
            return RedirectResponse(url="/docs")

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="localhost", port=8389)
