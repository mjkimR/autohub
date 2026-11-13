"""Explicit acknowledgment of retired ownership; no execution or remote effects."""

from typing import Annotated

from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES, RunResumeReceipt
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends

from .activity_claims import lease_valid
from .batch_repo import BatchRepository
from .execution import EXECUTION_VERSION, retired
from .schemas import ClaimRead


def claim_view(row):
    return ClaimRead(
        id=row.id,
        project_id=row.project_id,
        unit=row.unit,
        activity=row.activity,
        run_id=row.run_id,
        settled=row.settled,
        retired=row.checkpoint.get("execution_version") != EXECUTION_VERSION or bool(row.checkpoint.get("retired")),
        checkpoint_digest=request_digest(row.checkpoint),
        checkpoint={key: value for key, value in row.checkpoint.items() if key != "lease"},
    )


def acknowledge_run(run, actor, request_id):
    if not retired(run) or run.state not in FINAL_RUN_STATES:
        raise ProjectError(409, "Inspect a terminal retired Run before reconciling external work")
    progress = dict(run.sdd_progress or {})
    retirement = dict(progress.get("retirement") or {})
    retirement.update(
        external_work_unreconciled=False,
        actor=actor,
        request_id=str(request_id),
        reconciled_at=get_current_utc_time().isoformat(),
    )
    run.sdd_progress = {**progress, "retirement": retirement}
    run.revision += 1


class SddClaimHistory:
    def __init__(self, projects: Annotated[ProjectService, Depends()]):
        self.projects, self.repo, self.runs = projects, BatchRepository(), PipelineRunRepository()

    async def get(self, project_id, claim_id):
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id)
            row = await self.repo.claim(session, project_id, claim_id)
            if row is None:
                raise ProjectError(404, "Activity claim not found")
            return claim_view(row)

    async def reconcile(self, project_id, claim_id, request, actor):
        digest = request_digest(request.model_dump(mode="json"))
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id, lock=True)
            row = await self.repo.claim(session, project_id, claim_id, lock=True)
            if row is None:
                raise ProjectError(404, "Activity claim not found")
            cp = dict(row.checkpoint)
            previous = cp.get("reconciliation")
            if previous:
                if (
                    previous.get("request_id") != str(request.request_id)
                    or previous.get("actor") != actor
                    or previous.get("request_digest") != digest
                ):
                    raise ProjectError(409, "Claim reconciliation already records a different request")
                return claim_view(row)
            if (
                cp.get("execution_version") == EXECUTION_VERSION
                and not cp.get("retired")
                and (row.run_id is not None or not cp.get("uncertain") or lease_valid(cp))
            ):
                raise ProjectError(
                    409,
                    "Only an uncertain activity without a Run or live lease can be settled; inspect its current owner",
                )
            if request.expected_checkpoint_digest != request_digest(cp):
                raise ProjectError(409, "Claim evidence changed; inspect the retained candidate again")
            if row.run_id:
                run = await self.runs.get(session, row.run_id, lock=True)
                if (
                    run is None
                    or run.project_id != project_id
                    or (run.sdd_snapshot or {}).get("spec_dir") != row.unit
                    or (cp.get("pull_number") and cp["pull_number"] != run.pull_number)
                ):
                    raise ProjectError(409, "Claim and retained Run do not identify the same inspected work")
                acknowledge_run(run, actor, request.request_id)
            row.settled = True
            row.checkpoint = {
                **cp,
                "retired": True,
                "lease": None,
                "lease_expires_at": None,
                "reconciliation": {
                    "request_id": str(request.request_id),
                    "actor": actor,
                    "request_digest": digest,
                    "checkpoint_digest": request.expected_checkpoint_digest,
                    "reconciled_at": get_current_utc_time().isoformat(),
                },
            }
            await session.flush()
            return claim_view(row)

    async def reconcile_run(self, project_id, run_id, request, actor):
        digest = request_digest({"run_id": str(run_id), "actor": actor, "request": request.model_dump(mode="json")})
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id, lock=True)
            run = await self.runs.get(session, run_id, lock=True)
            if run is None or run.project_id != project_id:
                raise ProjectError(404, "Retained Run not found")
            receipt = await session.get(RunResumeReceipt, request.request_id)
            if receipt:
                if receipt.pipeline_run_id != run_id or receipt.request_digest != digest:
                    raise ProjectError(409, "Reconciliation request ID belongs to another operation")
                return PipelineRunRead.model_validate(run)
            if run.revision != request.expected_revision:
                raise ProjectError(409, "Run evidence changed; inspect its current revision")
            if not (run.sdd_progress or {}).get("retirement", {}).get("external_work_unreconciled"):
                raise ProjectError(409, "Run has no unreconciled retired external work")
            acknowledge_run(run, actor, request.request_id)
            session.add(
                RunResumeReceipt(
                    id=request.request_id,
                    pipeline_run_id=run_id,
                    request_digest=digest,
                    decision_evidence={
                        "action": "reconcile-retired-execution",
                        "actor": actor,
                        "revision": request.expected_revision,
                    },
                )
            )
            await session.flush()
            # Match the persisted timestamp representation used by replay reads, including SQLite.
            await session.refresh(run)
            return PipelineRunRead.model_validate(run)
