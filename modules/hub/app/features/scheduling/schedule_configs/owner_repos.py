"""Bounded owner lookups and correlated project selection, without UUID casts."""

from uuid import UUID

from app.features.project_management.agent_schedules.models import ProjectAgentSchedule
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.projects.models import Project
from sqlalchemy import String, and_, cast, exists, func, or_, select

from .models import ScheduleConfig
from .ownership import RESERVED


def payload_uuid_matches(key: str, value: UUID):
    # JSON text retains quotes for strings on both dialects, excluding numbers/arrays/objects.
    text = func.lower(cast(ScheduleConfig.payload[key], String))
    return text.in_([f'"{value}"', f'"{value.hex}"'])


def project_filter(project_id: UUID):
    agents = exists().where(ProjectAgentSchedule.schedule_config_id == ScheduleConfig.id)
    agent_for_project = exists().where(
        ProjectAgentSchedule.schedule_config_id == ScheduleConfig.id, ProjectAgentSchedule.project_id == project_id
    )
    # Matching payload UUID text against a retained test's UUID uses its canonical and hex forms.
    test_text = func.lower(cast(ScheduleConfig.payload["test_id"], String))
    test_id = func.lower(cast(ConnectionTest.id, String))
    canonical = (
        func.substr(func.replace(test_id, "-", ""), 1, 8)
        + "-"
        + func.substr(func.replace(test_id, "-", ""), 9, 4)
        + "-"
        + func.substr(func.replace(test_id, "-", ""), 13, 4)
        + "-"
        + func.substr(func.replace(test_id, "-", ""), 17, 4)
        + "-"
        + func.substr(func.replace(test_id, "-", ""), 21, 12)
    )
    test_match = exists().where(
        ConnectionTest.project_id == project_id,
        or_(test_text == '"' + canonical + '"', test_text == '"' + func.replace(test_id, "-", "") + '"'),
    )
    return and_(
        exists().where(Project.id == project_id),
        or_(
            and_(
                ScheduleConfig.task_func == "pipeline.dispatch_project", payload_uuid_matches("project_id", project_id)
            ),
            and_(ScheduleConfig.task_func == "pipeline.connection_test", test_match),
            and_(ScheduleConfig.task_func.not_in(list(RESERVED)), agent_for_project),
            and_(
                ScheduleConfig.task_func == "pipeline.observe_project",
                ~agents,
                payload_uuid_matches("project_id", project_id),
            ),
        ),
    )


class ScheduleOwnerRepository:
    async def agents(self, session, ids):
        return (
            (
                await session.execute(
                    select(ProjectAgentSchedule).where(ProjectAgentSchedule.schedule_config_id.in_(ids))
                )
            )
            .scalars()
            .all()
        )

    async def tests(self, session, ids):
        return (
            (await session.execute(select(ConnectionTest).where(ConnectionTest.id.in_(ids)))).scalars().all()
            if ids
            else []
        )

    async def projects(self, session, ids):
        return (
            set((await session.execute(select(Project.id).where(Project.id.in_(ids)))).scalars().all())
            if ids
            else set()
        )
