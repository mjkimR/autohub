"""Retired bridge attempts can only observe a PR they already resumed."""

from uuid import UUID

from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, get_credential_key_provider
from app.features.configuration.connectors.repos import ConnectorRepository
from app.features.configuration.connectors.usecases.token import ReadConnectorTokenUseCase
from app.features.project_management.pipeline_runs.models import PipelineRun, PipelineRunState, RunResumeReceipt
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.control import PipelineRunControl
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time

from .adapters import RETIRED_BRIDGE, WorkerAction, WorkerResult
from .errors import FlowError
from .models import FlowPRLink, FlowRun
from .runtime import utc


def control():
    observer = PipelineObservationService(
        ReadConnectorTokenUseCase(
            ConnectorRepository(), ConnectorCredentialCipher(get_credential_key_provider())
        ).execute
    )
    return PipelineRunControl(PipelineRunRepository(), ProjectService(ProjectRepository()), observer)


class PRBridgeWorker:
    async def guard(self, session, action):
        run = await session.get(FlowRun, action.run_id, with_for_update=True, populate_existing=True)
        if (
            run is None
            or run.revision != action.revision
            or run.lease_expires_at is None
            or utc(run.lease_expires_at) <= get_current_utc_time()
        ):
            raise FlowError(409, "bridge-stale", "flow changed before retired bridge observation")
        return run

    async def execute(self, action: WorkerAction) -> WorkerResult:
        failed = WorkerResult(attempt_id=action.attempt_id, status="failed", error=RETIRED_BRIDGE)
        try:
            pipeline_id = UUID(str(action.inputs["pipeline_run_id"]))
        except (KeyError, ValueError, TypeError):
            return failed
        async with AsyncTransaction() as session:
            await self.guard(session, action)
            link = await session.get(FlowPRLink, pipeline_id, with_for_update=True)
            if link is None or link.flow_run_id != action.run_id:
                return failed
            receipt = await session.get(RunResumeReceipt, action.attempt_id)
            resumed = (
                action.binding.get("target", "").startswith("autohub.pr_delivery:")
                and link.delivery_attempt_id == action.attempt_id
                and receipt is not None
                and receipt.pipeline_run_id == pipeline_id
            )
            if not resumed:
                link.canceled = True
                return (
                    WorkerResult(attempt_id=action.attempt_id, status="canceled")
                    if action.operation == "cancel"
                    else failed
                )
            if action.operation == "cancel":
                link.canceled = True
            elif link.canceled:
                return failed
            pipeline = await session.get(PipelineRun, pipeline_id, populate_existing=True)
            if pipeline is None:
                return WorkerResult(attempt_id=action.attempt_id, status="failed", error="pr-run-missing")
            terminal = pipeline.state in ("completed", "failed", "canceled")
            output = {
                "pipeline_run_id": str(pipeline.id),
                "state": pipeline.state,
                "head_sha": pipeline.pull_snapshot.get("head_sha"),
            }
        if action.operation == "cancel":
            if not terminal:
                await control().cancel_run(pipeline_id)
            return WorkerResult(attempt_id=action.attempt_id, status="canceled")
        if output["state"] == PipelineRunState.COMPLETED:
            return WorkerResult(attempt_id=action.attempt_id, status="completed", output=output)
        if output["state"] in (PipelineRunState.FAILED, PipelineRunState.CANCELED):
            return WorkerResult(
                attempt_id=action.attempt_id, status="failed", output=output, error=f"pr-{output['state']}"
            )
        return WorkerResult(
            attempt_id=action.attempt_id,
            status="pending",
            output=output,
            error=f"pr-{output['state']}" if output["state"] in ("paused", "blocked") else None,
        )
