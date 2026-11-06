"""Fair, bounded SDD coordination inside the existing maintenance owner."""

from app.features.configuration.system_configs.models import SystemConfig
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService
from app.features.project_management.sdd.batch_driver import BatchDriver
from app.features.project_management.sdd.batch_models import SddBatch
from app.features.project_management.sdd.batch_usecases import SddBatchUseCase
from app.features.project_management.sdd.usecases import SddUseCase
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.core.log import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

CHECKPOINT = "maintenance.sdd-batches"


async def maintain_batches(observer):
    projects = ProjectService(ProjectRepository())
    runs = PipelineRunUseCase(PipelineRunRepository(), projects, observer)
    driver = BatchDriver(SddBatchUseCase(projects, SddUseCase(projects, observer, runs)))
    async with AsyncTransaction() as session:
        insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
        await session.execute(
            insert(SystemConfig).values(name=CHECKPOINT, data={}).on_conflict_do_nothing(index_elements=["name"])
        )
        cursor = await session.scalar(select(SystemConfig).where(SystemConfig.name == CHECKPOINT).with_for_update())
        assert cursor is not None
        after = (cursor.data or {}).get("after")
        stmt = select(SddBatch).where(SddBatch.exclusion).order_by(SddBatch.id).limit(4)
        rows = list(await session.scalars(stmt.where(SddBatch.id > after) if after else stmt))
        if not rows and after:
            rows = list(await session.scalars(stmt))
        ids = [(r.project_id, r.id) for r in rows]
        if ids:
            cursor.data = {"after": str(ids[-1][1])}
    for project_id, batch_id in ids:
        try:
            await driver.tick(project_id, batch_id)
        except Exception:
            logger.exception("SDD batch reconciliation will retry the same admission")
