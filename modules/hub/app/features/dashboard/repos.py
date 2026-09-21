from app.features.configuration.connectors.models import Connector
from app.features.dashboard.schemas import DashboardStats
from app.features.project_management.pipeline_runs.models import PipelineRun, PipelineRunState
from app.features.project_management.projects.models import Project
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class DashboardRepository:
    async def stats(self, session: AsyncSession) -> DashboardStats:
        # Scalar subqueries keep all counters on the same statement snapshot, without loading history.
        run_counts = [
            select(func.count()).select_from(PipelineRun).where(PipelineRun.state == state).scalar_subquery()
            for state in PipelineRunState
        ]
        row = (
            await session.execute(
                select(
                    select(func.count()).select_from(Project).scalar_subquery(),
                    select(func.count()).select_from(ScheduleConfig).scalar_subquery(),
                    select(func.count()).select_from(Connector).scalar_subquery(),
                    select(func.count()).select_from(Connector).where(Connector.enabled.is_(True)).scalar_subquery(),
                    *run_counts,
                )
            )
        ).one()
        counts = dict(zip(PipelineRunState, row[4:], strict=True))
        return DashboardStats(
            project_count=row[0],
            schedule_count=row[1],
            connector_count=row[2],
            active_connector_count=row[3],
            total_runs=sum(counts.values()),
            runs_by_state=counts,
        )
