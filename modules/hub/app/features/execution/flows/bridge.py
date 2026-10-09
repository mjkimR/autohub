"""Observe a single existing PR owner; never create another PR run or merge controller."""

from uuid import UUID

from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, get_credential_key_provider
from app.features.configuration.connectors.repos import ConnectorRepository
from app.features.configuration.connectors.usecases.token import ReadConnectorTokenUseCase
from app.features.project_management.pipeline_runs.interaction_schemas import ResumeRunRequest
from app.features.project_management.pipeline_runs.models import PipelineRun, PipelineRunState, RunResumeReceipt
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.control import PipelineRunControl
from app.features.project_management.pipeline_runs.usecases.transitions import EXTERNAL_IMPLEMENTATION_STATUS
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from pydantic import BaseModel, ConfigDict, Field

from .adapters import WorkerAction, WorkerResult
from .errors import FlowError
from .evidence import BridgeRejected, read_evidence
from .models import FlowPRLink, FlowRun
from .runtime import utc
from .validation import digest as content_digest


class BridgeInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipeline_run_id: UUID
    pipeline_revision: int = Field(ge=1)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    spec_dir: str
    evidence_digest: str | None = None


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
            or run.status == "canceling"
            or run.revision != action.revision
            or run.lease_expires_at is None
            or utc(run.lease_expires_at) <= get_current_utc_time()
        ):
            raise FlowError(409, "bridge-stale", "flow changed before PR operation")
        return run

    async def execute(self, action: WorkerAction):
        try:
            data = BridgeInputs.model_validate(action.inputs)
            check = action.binding["target"].startswith("autohub.specrig:")
            if action.operation == "cancel":
                return await self.cancel(action, data)
            if check:
                return await self.check(action, data)
            return await self.deliver(action, data)
        except (BridgeRejected, ValueError, FileNotFoundError) as exc:
            error = str(exc) if isinstance(exc, BridgeRejected) else "bridge-input-or-checkout-invalid"
            return WorkerResult(attempt_id=action.attempt_id, status="failed", error=error)
        except ProjectError as exc:
            if exc.status >= 500:
                raise FlowError(503, "bridge-unavailable", "PR observation is unavailable") from exc
            return WorkerResult(attempt_id=action.attempt_id, status="failed", error="pr-resume-rejected")
        except (OSError, TimeoutError) as exc:
            raise FlowError(503, "bridge-unavailable", "checkout or PR worker is unavailable") from exc

    async def check(self, action, data):
        digest = await read_evidence(action.binding["checkout"], data.spec_dir, data.head_sha)
        output = {**data.model_dump(mode="json", exclude_none=True), "evidence_digest": digest}
        async with AsyncTransaction() as session:
            await self.guard(session, action)
            pipeline = await session.get(
                PipelineRun, data.pipeline_run_id, with_for_update=True, populate_existing=True
            )
            await self.check_pipeline(session, pipeline, action, data)
            link = await session.get(FlowPRLink, data.pipeline_run_id, with_for_update=True)
            if link is not None and link.flow_run_id != action.run_id:
                previous = await session.get(FlowRun, link.flow_run_id)
                if (
                    previous is None
                    or previous.status not in ("failed", "canceled")
                    or link.delivery_attempt_id is not None
                ):
                    raise BridgeRejected("pr-owned-by-another-flow")
                link.flow_run_id, link.evidence, link.canceled = action.run_id, output, False
            elif link is None:
                session.add(
                    FlowPRLink(pipeline_run_id=data.pipeline_run_id, flow_run_id=action.run_id, evidence=output)
                )
            else:
                if link.canceled:
                    raise BridgeRejected("pr-bridge-canceled")
                link.evidence = output
            if link is not None:
                link.approved_revision = link.approved_digest = link.approved_actor = None
        return WorkerResult(attempt_id=action.attempt_id, status="completed", output=output)

    async def check_pipeline(self, session, pipeline, action, data):
        if pipeline is None or str(pipeline.project_id) != action.binding["project_id"]:
            raise BridgeRejected("pr-project-mismatch")
        if pipeline.state != PipelineRunState.PAUSED or pipeline.revision != data.pipeline_revision:
            raise BridgeRejected("pr-must-be-paused-at-reviewed-revision")
        if pipeline.pull_snapshot.get("head_sha") != data.head_sha:
            raise BridgeRejected("pr-head-changed")
        attempts = await PipelineRunRepository().list_attempts(session, pipeline.id)
        if not attempts or attempts[-1].external_status != EXTERNAL_IMPLEMENTATION_STATUS:
            raise BridgeRejected("pr-must-be-externally-implemented")

    async def deliver(self, action, data):
        async with AsyncTransaction() as session:
            await self.guard(session, action)
            link = await session.get(FlowPRLink, data.pipeline_run_id, with_for_update=True)
            if link is None or link.flow_run_id != action.run_id or link.canceled:
                raise BridgeRejected("pr-bridge-owner-mismatch")
            if (
                link.approved_revision is None
                or link.approved_digest != content_digest(link.evidence)
                or not link.approved_actor
            ):
                raise BridgeRejected("pr-resume-approval-required")
            if link.evidence != data.model_dump(mode="json", exclude_none=True):
                raise BridgeRejected("pr-evidence-mismatch")
            if link.delivery_attempt_id not in (None, action.attempt_id):
                raise BridgeRejected("pr-attempt-mismatch")
            link.delivery_attempt_id = action.attempt_id
            resumed = await session.get(RunResumeReceipt, action.attempt_id) is not None
            actor = f"sdk-flow:{action.run_id};approval:{link.approved_actor}"
        if not resumed:
            digest = await read_evidence(action.binding["checkout"], data.spec_dir, data.head_sha)
            if digest != data.evidence_digest:
                raise BridgeRejected("approved-evidence-changed")

            async def guard(session, pipeline):
                await self.guard(session, action)
                link = await session.get(FlowPRLink, data.pipeline_run_id)
                if link is None or link.flow_run_id != action.run_id or link.canceled:
                    raise FlowError(409, "bridge-stale", "PR owner changed before resume")
                if str(pipeline.project_id) != action.binding["project_id"]:
                    raise BridgeRejected("pr-project-mismatch")

            await control().resume_run(
                data.pipeline_run_id,
                request=ResumeRunRequest(
                    request_id=action.attempt_id,
                    expected_revision=data.pipeline_revision,
                ),
                actor=actor,
                expected_head_sha=data.head_sha,
                guard=guard,
            )
        async with AsyncTransaction() as session:
            pipeline = await session.get(PipelineRun, data.pipeline_run_id, populate_existing=True)
            if pipeline is None:
                raise BridgeRejected("pr-run-missing")
            output = {
                "pipeline_run_id": str(pipeline.id),
                "state": pipeline.state,
                "head_sha": pipeline.pull_snapshot.get("head_sha", data.head_sha),
            }
            if pipeline.state == PipelineRunState.COMPLETED:
                status, error = "completed", None
            elif pipeline.state in (PipelineRunState.FAILED, PipelineRunState.CANCELED):
                status, error = "failed", f"pr-{pipeline.state}"
            else:
                status, error = "pending", f"pr-{pipeline.state}" if pipeline.state in ("paused", "blocked") else None
        return WorkerResult(attempt_id=action.attempt_id, status=status, output=output, error=error)

    async def cancel(self, action, data):
        should_cancel = False
        async with AsyncTransaction() as session:
            link = await session.get(FlowPRLink, data.pipeline_run_id, with_for_update=True)
            if link is not None and link.flow_run_id == action.run_id:
                link.canceled = True
                should_cancel = link.delivery_attempt_id is not None
        if should_cancel:
            async with AsyncTransaction() as session:
                pipeline = await session.get(PipelineRun, data.pipeline_run_id, populate_existing=True)
                terminal = pipeline is None or pipeline.state in ("completed", "failed", "canceled")
            if not terminal:
                await control().cancel_run(data.pipeline_run_id)
        # A tombstone fences later resume of this attempt. PR ownership stops;
        # previously posted external agent requests/effects cannot be rolled back.
        return WorkerResult(attempt_id=action.attempt_id, status="canceled")
