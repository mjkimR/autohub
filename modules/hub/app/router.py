from typing import Annotated

from app.auth import require_scheduler_or_user, require_user
from app.features.ai_catalogs.api.v1 import router as v1_ai_catalogs_router
from app.features.configuration.connectors.api.v1 import router as v1_connectors_router
from app.features.configuration.system_configs.api.v1 import router as v1_system_configs_router
from app.features.configuration.system_configs.models import SystemConfig
from app.features.dashboard.api import router as v1_dashboard_router
from app.features.execution.dispatchers.api.v1 import router as v1_dispatchers_router
from app.features.execution.dispatchers.usecases.housekeeping import HEARTBEAT_CONFIG, parse_instant, tick_status
from app.features.execution.tasks.api.v1 import router as v1_tasks_router
from app.features.notifications.api.v1 import router as v1_notification_channels_router
from app.features.project_management.agent_schedules.api.v1 import router as v1_agent_schedules_router
from app.features.project_management.connection_tests.api import router as v1_connection_tests_router
from app.features.project_management.github_webhooks.api import router as github_webhooks_router
from app.features.project_management.github_webhooks.api_v1 import router as v1_github_webhook_deliveries_router
from app.features.project_management.pipeline_runs.api.v1 import router as v1_pipeline_runs_router
from app.features.project_management.pipelines.api.v1 import router as v1_pipelines_router
from app.features.project_management.projects.api.v1 import router as v1_projects_router
from app.features.scheduling.schedule_configs.api.v1 import router as v1_schedule_configs_router
from app.features.scheduling.schedule_jobs.api.v1 import router as v1_schedule_jobs_router
from app_layer_base.core.database.deps import get_session
from app_layer_base.utils.time_util import get_current_utc_time
from app_prebuilt_api_key.api import api_keys_router
from app_prebuilt_user.api import v1_users_router
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api")
v1_router = APIRouter(prefix="/v1", dependencies=[Depends(require_user)])
# Signing in cannot require being signed in; the user routes guard themselves (a user, or a superuser).
v1_open_router = APIRouter(prefix="/v1")
# The scheduler holds a key of its own that opens this route and nothing else.
v1_trigger_router = APIRouter(prefix="/v1", dependencies=[Depends(require_scheduler_or_user)])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health():
    return {"status": "ok"}


@router.get("/health/deep", status_code=status.HTTP_200_OK)
async def deep_health_check(session: Annotated[AsyncSession, Depends(get_session)]):
    try:
        await session.execute(text("SELECT 1"))
        heartbeat = await session.scalar(select(SystemConfig.data).where(SystemConfig.name == HEARTBEAT_CONFIG))
        last_tick_at = parse_instant((heartbeat or {}).get("last_tick_at"))
        return {
            "status": "ok",
            "database": "connected",
            # "stale" means the external trigger stopped firing: the hub answers but advances nothing on a timer.
            "scheduler": tick_status(last_tick_at, get_current_utc_time()),
            "last_tick_at": last_tick_at.isoformat() if last_tick_at is not None else None,
        }
    except Exception:
        return Response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content="Database connection failed",
        )


# Feature routers
v1_router.include_router(v1_dashboard_router)
v1_router.include_router(v1_connectors_router)
v1_router.include_router(v1_pipelines_router)
v1_router.include_router(v1_pipeline_runs_router)
v1_router.include_router(v1_projects_router)
v1_router.include_router(v1_connection_tests_router)
v1_router.include_router(v1_agent_schedules_router)
v1_router.include_router(v1_github_webhook_deliveries_router)
v1_router.include_router(v1_schedule_configs_router)
v1_router.include_router(v1_system_configs_router)
v1_router.include_router(v1_notification_channels_router)
v1_router.include_router(v1_ai_catalogs_router)
v1_router.include_router(v1_schedule_jobs_router)
v1_trigger_router.include_router(v1_dispatchers_router)
v1_open_router.include_router(v1_users_router)
v1_open_router.include_router(api_keys_router)
v1_router.include_router(v1_tasks_router)
router.include_router(v1_router)
router.include_router(v1_trigger_router)
router.include_router(v1_open_router)
# GitHub authenticates this endpoint with its HMAC signature, not a signed-in user.
router.include_router(github_webhooks_router)
