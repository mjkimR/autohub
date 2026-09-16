"""Project agent schedules and the generic schedules they own.

Everything that derives a ``ScheduleConfig`` from a project and an agent schedule lives here, so the project service
can keep owned schedules in step without importing the agent-schedule service (which depends on the project service).
"""

from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID

from app.common.utils.calc_schedule import calc_next_run
from app.features.ai_catalogs.models import AICatalog, AICatalogKind
from app.features.project_management.agent_schedules.models import ProjectAgentSchedule
from app.features.project_management.projects.models import Project
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# The scheduler task that starts one session, by catalog kind. Kinds without one cannot have agent schedules.
SESSION_TASKS: dict[str, str] = {AICatalogKind.JULES: "jules.session"}
# The task that follows a kind's sessions to the end, kept once per catalog while any agent schedule uses it.
SYNC_TASKS: dict[str, str] = {AICatalogKind.JULES: "jules.sync_sessions"}
SYNC_INTERVAL_SECONDS = 300


def session_payload(project: Project, schedule: ProjectAgentSchedule, catalog: AICatalog) -> dict:
    """The owned schedule's payload: what the operator set plus what the project and catalog already know."""
    return {
        "catalog_key": catalog.key,
        "repository": project.github_repository,
        "starting_branch": schedule.starting_branch,
        "title": schedule.title,
        "prompt": schedule.prompt,
        "work_type": schedule.work_type,
    }


def _config_name(project: Project, schedule: ProjectAgentSchedule) -> str:
    return f"Agent {schedule.id.hex[:8]}: {schedule.title} ({project.name})"


class AgentScheduleRepository:
    async def get(self, session: AsyncSession, schedule_id: UUID, *, lock: bool = False) -> ProjectAgentSchedule | None:
        return await session.get(ProjectAgentSchedule, schedule_id, with_for_update=lock)

    async def list_for_project(self, session: AsyncSession, project_id: UUID) -> Sequence[ProjectAgentSchedule]:
        rows = await session.scalars(
            select(ProjectAgentSchedule)
            .where(ProjectAgentSchedule.project_id == project_id)
            .order_by(ProjectAgentSchedule.created_at, ProjectAgentSchedule.id)
        )
        return rows.all()

    async def owner_of_config(self, session: AsyncSession, schedule_config_id: UUID) -> ProjectAgentSchedule | None:
        return await session.scalar(
            select(ProjectAgentSchedule).where(ProjectAgentSchedule.schedule_config_id == schedule_config_id)
        )

    async def count_for_catalog(self, session: AsyncSession, catalog_id: UUID) -> int:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(ProjectAgentSchedule)
                .where(ProjectAgentSchedule.ai_catalog_id == catalog_id)
            )
            or 0
        )

    async def write_config(
        self, session: AsyncSession, project: Project, schedule: ProjectAgentSchedule, catalog: AICatalog
    ) -> ScheduleConfig:
        """Create or rewrite the owned schedule from its agent schedule. The trigger change recomputes the next run."""
        config = await session.get(ScheduleConfig, schedule.schedule_config_id) if schedule.schedule_config_id else None
        trigger_changed = config is None or (
            config.cron_expression != schedule.cron_expression or config.interval_seconds != schedule.interval_seconds
        )
        if config is None:
            config = ScheduleConfig(task_func=SESSION_TASKS[catalog.kind])
            session.add(config)
        config.name = _config_name(project, schedule)
        config.description = f"Agent schedule of project {project.name}"
        config.task_func = SESSION_TASKS[catalog.kind]
        config.cron_expression = schedule.cron_expression
        config.interval_seconds = schedule.interval_seconds
        config.payload = session_payload(project, schedule, catalog)
        config.enabled = schedule.enabled and project.enabled
        if trigger_changed:
            config.next_run_at = calc_next_run(schedule.cron_expression, schedule.interval_seconds)
        await session.flush([config])
        schedule.schedule_config_id = config.id
        await session.flush()
        return config

    async def resync_project(self, session: AsyncSession, project: Project) -> None:
        """Rewrite every owned schedule after a project change (name, repository, enabled)."""
        for schedule in await self.list_for_project(session, project.id):
            catalog = await session.get(AICatalog, schedule.ai_catalog_id)
            if catalog is not None:
                await self.write_config(session, project, schedule, catalog)

    async def delete(self, session: AsyncSession, schedule: ProjectAgentSchedule) -> None:
        config = await session.get(ScheduleConfig, schedule.schedule_config_id)
        catalog_id = schedule.ai_catalog_id
        await session.delete(schedule)
        if config is not None:
            await session.delete(config)
        await session.flush()
        await self.ensure_sync_schedule(session, catalog_id)

    async def delete_for_project(self, session: AsyncSession, project_id: UUID) -> None:
        for schedule in await self.list_for_project(session, project_id):
            await self.delete(session, schedule)

    async def ensure_sync_schedule(self, session: AsyncSession, catalog_id: UUID) -> None:
        """Keep exactly one sync schedule per catalog while any agent schedule uses it, and none otherwise."""
        catalog = await session.get(AICatalog, catalog_id)
        if catalog is None or (task := SYNC_TASKS.get(catalog.kind)) is None:
            return
        existing = (
            await session.scalars(
                select(ScheduleConfig).where(
                    ScheduleConfig.task_func == task,
                    ScheduleConfig.payload["catalog_key"].as_string() == catalog.key,
                )
            )
        ).all()
        wanted = await self.count_for_catalog(session, catalog_id) > 0
        if wanted and not existing:
            session.add(
                ScheduleConfig(
                    name=f"Sync sessions: {catalog.key}",
                    description=f"Follows {catalog.name} sessions started by agent schedules to the end",
                    task_func=task,
                    interval_seconds=SYNC_INTERVAL_SECONDS,
                    payload={"catalog_key": catalog.key},
                    enabled=True,
                    next_run_at=get_current_utc_time() + timedelta(seconds=SYNC_INTERVAL_SECONDS),
                )
            )
        elif not wanted:
            for config in existing:
                await session.delete(config)
        await session.flush()
