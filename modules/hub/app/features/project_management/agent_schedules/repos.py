"""Project agent schedules and the generic schedules they own.

Everything that derives a ``ScheduleConfig`` from a project and an agent schedule lives here, so the project service
can keep owned schedules in step without importing the agent-schedule service (which depends on the project service).
"""

from collections.abc import Iterable, Sequence
from uuid import UUID

from app.common.utils.calc_schedule import calc_next_run
from app.features.ai_catalogs.models import AICatalog, AICatalogKind
from app.features.project_management.agent_schedules.models import ProjectAgentSchedule
from app.features.project_management.projects.models import Project
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# The scheduler task that starts one session, by catalog kind. Kinds without one cannot have agent schedules.
SESSION_TASKS: dict[str, str] = {AICatalogKind.JULES: "jules.session"}


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

    async def write_config(
        self, session: AsyncSession, project: Project, schedule: ProjectAgentSchedule, catalog: AICatalog
    ) -> ScheduleConfig:
        """Create or rewrite the owned schedule from its agent schedule.

        The next run is recomputed when the trigger changes and when the entry turns on, so a stale due time from
        before it was disabled never fires the moment it is re-enabled.
        """
        config = await session.get(ScheduleConfig, schedule.schedule_config_id) if schedule.schedule_config_id else None
        # A project that lost its GitHub connection has no repository to start sessions on.
        enabled = bool(
            schedule.enabled and project.enabled and catalog.enabled and project.github_repository is not None
        )
        recompute_next_run = config is None or (
            config.cron_expression != schedule.cron_expression
            or config.interval_seconds != schedule.interval_seconds
            or (enabled and not config.enabled)
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
        config.enabled = enabled
        if recompute_next_run:
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

    async def resync_catalog(self, session: AsyncSession, catalog: AICatalog) -> None:
        """Rewrite every owned schedule after a catalog change (enabled)."""
        rows = await session.scalars(
            select(ProjectAgentSchedule).where(ProjectAgentSchedule.ai_catalog_id == catalog.id)
        )
        for schedule in rows.all():
            project = await session.get(Project, schedule.project_id)
            if project is not None:
                await self.write_config(session, project, schedule, catalog)

    async def lock_catalogs(self, session: AsyncSession, catalog_ids: Iterable[UUID]) -> None:
        """Lock catalogs in id order before their owned configs are written.

        Every writer takes catalog locks before config rows (the catalog service locks its catalog first, then
        rewrites configs), so taking them here first, in one order, rules out deadlocks between the two paths.
        """
        for catalog_id in sorted(set(catalog_ids)):
            await session.get(AICatalog, catalog_id, with_for_update=True)

    async def delete(self, session: AsyncSession, schedule: ProjectAgentSchedule) -> None:
        await self.lock_catalogs(session, [schedule.ai_catalog_id])
        config = await session.get(ScheduleConfig, schedule.schedule_config_id)
        await session.delete(schedule)
        if config is not None:
            await session.delete(config)
        await session.flush()

    async def delete_for_project(self, session: AsyncSession, project_id: UUID) -> None:
        for schedule in await self.list_for_project(session, project_id):
            await self.delete(session, schedule)
