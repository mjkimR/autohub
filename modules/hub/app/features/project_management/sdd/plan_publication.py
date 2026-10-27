"""Durable proposal decisions: prepare locally, fence publication, reconcile an uncertain push."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.features.project_management.pipeline_runs.interaction_repo import RunInteractionRepository
from app.features.project_management.pipeline_runs.interaction_service import RunInteractionService, check_revision
from app.features.project_management.pipeline_runs.models import RunResumeReceipt
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import select

from .gates import PLAN_ACCEPT_REQUEST
from .plan_decisions import plan_approval, record_plan_decision
from .services import SddService
from .units import is_proposal

LEASE_SECONDS = 240


class PlanDecisionPublisher:
    def __init__(self, repo, projects, observer):
        self.repo, self.projects, self.observer = repo, projects, observer

    @staticmethod
    def validate(run, project, revision, lease=None):
        check_revision(run, revision)
        if run.state not in ("paused", "blocked", "implementing"):
            raise ProjectError(409, "The proposal run is no longer waiting or executing")
        if (
            not project.enabled
            or (project.github_repository, project.github_connector_id)
            != (run.github_repository, run.github_connector_id)
            or project.revision != run.project_revision
        ):
            raise ProjectError(409, "Project changed during decision")
        if lease and (
            (run.lease_owner, str(run.lease_token)) != lease
            or not run.lease_expires_at
            or as_utc(run.lease_expires_at) <= get_current_utc_time()
        ):
            raise ProjectError(409, "Pipeline run lease changed during proposal decision")

    async def authorize(self, session, run, project, revision, *, automatic=False, lease=None):
        self.validate(run, project, revision, lease=lease)
        await RunInteractionService().response_for_resume(session, run, None)
        if automatic and (run.sdd_progress or {}).get("approval_withheld"):
            raise ProjectError(409, "Proposal approval was withdrawn; explicit reapproval is required")

    async def recover(self, run_id, pull, *, preserve_lease=False, request_id=None, lease=None, session=None):
        """Exact prepared commit identity is evidence of publication, never evidence of renewed approval."""
        async with AsyncTransaction(session=session) as session:
            run = await self.repo.get(session, run_id, lock=True)
            query = select(RunResumeReceipt).where(RunResumeReceipt.pipeline_run_id == run_id)
            if request_id is not None:
                query = query.where(RunResumeReceipt.id == request_id)
            rows = await session.scalars(query)
            for row in rows:
                data = dict(row.decision_evidence or {})
                publication = data.get("publication") or {}
                if publication.get("state") not in ("preparing", "prepared", "uncertain"):
                    continue
                plan = next(
                    (p for p in publication.get("candidates", []) if p["commit_sha"] == pull["head"]["sha"]), None
                )
                if plan is None:
                    continue
                project = await self.projects.get(session, run.project_id, lock=True)
                if lease:
                    self.validate(run, project, run.revision, lease=lease)
                applicable = (
                    pull.get("state") == "open"
                    and run.revision == publication.get("recovery_revision", data["revision"])
                    and pull["head"].get("ref") == plan.get("branch")
                    and pull["base"]["sha"] == (data.get("inspected_evidence") or {}).get("base_sha")
                    and run.state in ("paused", "blocked", "implementing")
                    and project.enabled
                    and project.revision == data["project_revision"]
                    and (project.github_repository, project.github_connector_id)
                    == (run.github_repository, run.github_connector_id)
                    and not await RunInteractionRepository().pending(session, run_id)
                    and not (plan.get("authority") == "policy" and (run.sdd_progress or {}).get("approval_withheld"))
                )
                await self.finish(session, run, row, plan, applicable=applicable, preserve_lease=preserve_lease)
                return PipelineRunRead.model_validate(run)
        return None

    async def finish(self, session, run, receipt, plan, *, applicable, preserve_lease=False):
        data = dict(receipt.decision_evidence or {})
        publication = {**data["publication"], "state": "published", "applied": applicable}
        receipt.decision_evidence = {**data, "publication": publication, "plan_decision": plan}
        if applicable:
            evidence = {
                **(data.get("inspected_evidence") or run.sdd_progress or {}),
                "plan_decision": plan,
                "approval": plan_approval(plan),
            }
            evidence.pop("approval_withheld", None)
            evidence.pop("waiting_for_approval", None)
            run.sdd_progress = evidence
            run.state, run.pause_reason = "awaiting_ci", None
            if not preserve_lease:
                run.lease_owner = run.lease_token = run.lease_expires_at = None
            # A push starts a new CI observation; do not reuse pre-publication CI in this advancement loop.
            run.next_action_at = get_current_utc_time() + timedelta(seconds=5)
            run.revision += 1
        await session.flush()

    async def decide(self, run_id, request, actor, *, automatic=False, inspected=None, lease=None):
        if request.workflow_answer or request.answer_id:
            raise ProjectError(422, "Apply the proposal decision separately from other answers")
        if not request.head_sha:
            raise ProjectError(422, "Confirm the inspected pull request head before deciding")
        digest = request_digest({"run_id": str(run_id), "actor": actor, "request": request.model_dump(mode="json")})
        owner = str(uuid4())
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            receipt = await session.get(RunResumeReceipt, request.request_id)
            if receipt and (receipt.pipeline_run_id != run_id or receipt.request_digest != digest):
                raise ProjectError(409, "Resume request ID was already used for different input")
            data = dict(receipt.decision_evidence or {}) if receipt else {}
            publication = data.get("publication") or {}
            if receipt and publication.get("state") not in ("preparing", "prepared", "uncertain"):
                return PipelineRunRead.model_validate(run)
            project = await self.projects.get(session, run.project_id)
            repository, connector, number = run.github_repository, run.github_connector_id, run.pull_number
            previous, snapshot = (
                dict(inspected if automatic and inspected is not None else run.sdd_progress or {}),
                dict(run.sdd_snapshot or {}),
            )
            if snapshot.get("provider") != "devkit-spec" or not is_proposal(snapshot.get("spec_dir", "")):
                raise ProjectError(422, "Proposal decisions require a native proposal run")
        # Always reconcile before checking the old revision: a push may have succeeded before the process died.
        pull = await self.observer.get_pull_request(connector, repository, number)
        if recovered := await self.recover(
            run_id, pull, preserve_lease=automatic, request_id=request.request_id, lease=lease
        ):
            return recovered
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            receipt = await session.get(RunResumeReceipt, request.request_id)
            if receipt and (receipt.pipeline_run_id != run_id or receipt.request_digest != digest):
                raise ProjectError(409, "Resume request ID was already used for different input")
            if receipt and (receipt.decision_evidence or {}).get("publication", {}).get("state") == "published":
                return PipelineRunRead.model_validate(run)
            project = await self.projects.get(session, run.project_id)
            await self.authorize(session, run, project, request.expected_revision, automatic=automatic, lease=lease)
            if not automatic and run.state not in ("paused", "blocked"):
                raise ProjectError(409, "Inspect the current wait before submitting a decision")
            if pull.get("state") != "open" or not request.head_sha or pull["head"]["sha"] != request.head_sha:
                raise ProjectError(409, "Pull request head changed; inspect and decide again")
            now = get_current_utc_time()
            data = dict(receipt.decision_evidence or {}) if receipt else {}
            publication = data.get("publication") or {}
            if publication.get("owner") and as_utc(datetime.fromisoformat(publication["expires_at"])) > now:
                raise ProjectError(
                    409,
                    "Proposal decision is being prepared; retry the same request shortly",
                    code="SDD_DECISION_IN_PROGRESS",
                )
            publication = {
                **publication,
                "state": "preparing",
                "owner": owner,
                "expires_at": (now + timedelta(seconds=LEASE_SECONDS)).isoformat(),
            }
            data = {
                "actor": actor,
                "action": request.decision,
                "feedback": request.feedback,
                "revision": run.revision,
                "project_revision": project.revision,
                "head_sha": request.head_sha,
                "publication": publication,
                "request": request.model_dump(mode="json"),
                "automatic": automatic,
            }
            if receipt is None:
                receipt = RunResumeReceipt(id=request.request_id, pipeline_run_id=run_id, request_digest=digest)
                session.add(receipt)
            receipt.decision_evidence = data
            await session.flush()
        try:
            token = await self.observer.get_token(connector, "github")
            evidence = await SddService().inspect(repository, snapshot["spec_dir"], pull, token, snapshot=snapshot)
            if evidence["evidence_digest"] != previous.get("evidence_digest"):
                raise ProjectError(409, "Workflow evidence changed; inspect again before deciding")
            if automatic:
                if evidence.get("base_policy", {}).get("approvals", {}).get("plan-accept", {}).get("policy") != "auto":
                    raise ProjectError(409, "The owning base has not delegated plan-accept")
                if evidence["snapshot"]["policy"].get("approvals", {}).get("plan-accept", {}).get("policy") != "auto":
                    raise ProjectError(409, "The proposal no longer delegates plan-accept")
            elif evidence.get("unit_status") != "reviewing":
                raise ProjectError(409, "Only a reviewing proposal can be decided")
            if request.decision == "accept_plan":
                if evidence.get("hold", {}).get("blocked") or evidence["current"].get("pending_questions"):
                    raise ProjectError(409, "Resolve the worker problem or answer its questions before accepting")
                if not automatic and not any(
                    r["id"] == PLAN_ACCEPT_REQUEST for r in evidence["current"].get("requests", [])
                ):
                    raise ProjectError(409, "Proposal is not waiting for acceptance")
            elif not (request.feedback or "").strip():
                raise ProjectError(422, "Give the rejection reason; it is kept in the commit message")
            await record_plan_decision(
                SddService(),
                repository,
                snapshot["spec_dir"],
                pull,
                token,
                decision=request.decision,
                actor=actor,
                note=request.feedback or "",
                snapshot=snapshot,
                expected_digest=evidence["evidence_digest"],
                request_id=str(request.request_id),
                authority="policy" if automatic else "user",
                publication=lambda plan: self.publication(
                    run_id, request.request_id, owner, plan, evidence, lease=lease
                ),
            )
        except BaseException:
            # Keep prepared candidates on failure: a timed-out push has an unknown external outcome.
            async with AsyncTransaction() as session:
                await self.repo.get(session, run_id, lock=True)
                receipt = await session.get(RunResumeReceipt, request.request_id)
                assert receipt is not None  # committed intent outlives preparation, including a failed push
                data = dict(receipt.decision_evidence or {})
                publication = data.get("publication") or {}
                if publication.get("owner") == owner and publication.get("state") != "published":
                    receipt.decision_evidence = {
                        **data,
                        "publication": {
                            **publication,
                            "state": "uncertain",
                            "expires_at": get_current_utc_time().isoformat(),
                        },
                    }
            raise
        async with AsyncTransaction() as session:
            return PipelineRunRead.model_validate(await self.repo.get(session, run_id))

    @asynccontextmanager
    async def publication(self, run_id, request_id: UUID, owner, plan, evidence, *, lease=None):
        # Persist the exact candidate before the external effect. A crash cannot erase its identity.
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            receipt = await session.get(RunResumeReceipt, request_id)
            assert receipt is not None
            data = dict(receipt.decision_evidence or {})
            publication = data["publication"]
            if publication.get("owner") != owner:
                raise ProjectError(409, "Proposal publication ownership changed")
            receipt.decision_evidence = {
                **data,
                "inspected_evidence": evidence,
                "publication": {
                    **publication,
                    "state": "prepared",
                    "candidates": [*publication.get("candidates", []), plan],
                },
            }
        # A bounded Git push is the only external I/O under these locks. Cancel/disable linearize before or after it.
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            project = await self.projects.get(session, run.project_id, lock=True)
            receipt = await session.get(RunResumeReceipt, request_id)
            assert receipt is not None
            data = dict(receipt.decision_evidence or {})
            if data["publication"].get("owner") != owner:
                raise ProjectError(409, "Proposal publication ownership changed")
            await self.authorize(
                session, run, project, data["revision"], automatic=data.get("automatic", False), lease=lease
            )
            if project.revision != data["project_revision"]:
                raise ProjectError(409, "Project changed during decision")
            yield
            await self.finish(session, run, receipt, plan, applicable=True, preserve_lease=lease is not None)
