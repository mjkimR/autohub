from uuid import UUID

from app.features.project_management.pipeline_runs.outcome_schemas import DecisionOutcome, Operation
from app.features.project_management.pipeline_runs.outcome_service import DecisionOutcomeService
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time


class DecisionOutcomeUseCase:
    async def get(self, run_id: UUID, request_id: UUID, operation: Operation) -> DecisionOutcome:
        async with AsyncTransaction() as session:
            # Run lock gives one coherent owner snapshot while mutations use the same lock.
            run = await PipelineRunRepository().get(session, run_id, lock=True)
            if run is None:
                raise ProjectError(404, "Pipeline run not found")
            progress = run.sdd_progress or {}
            evidence = await DecisionOutcomeService().evidence(session, run, request_id, operation)
            return DecisionOutcome(
                operation=operation,
                request_id=request_id,
                run_id=run_id,
                run_revision=run.revision,
                run_state=run.state,
                observed_at=get_current_utc_time(),
                inspected_head=progress.get("head_sha"),
                inspected_digest=progress.get("evidence_digest"),
                current_authority=progress.get("approval"),
                current_hold=progress.get("hold"),
                **evidence,
            )
