"""Typed decisions reuse PipelineRun locking, questions and durable resume receipts."""

from app.features.project_management.pipeline_runs.interaction_service import RunInteractionService, check_revision
from app.features.project_management.pipeline_runs.models import RunResumeReceipt
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time

from .progress import SpecrigProgress, approval_gate
from .services import SpecrigService


class SpecrigControl:
    def __init__(self, repo, projects, observer):
        self.repo, self.projects, self.observer = repo, projects, observer

    async def resume(self, run_id, request, actor):
        digest = request_digest({"run_id": str(run_id), "actor": actor, "request": request.model_dump(mode="json")})

        async def replay(session, run):
            receipt = await session.get(RunResumeReceipt, request.request_id)
            if receipt:
                if receipt.pipeline_run_id != run_id or receipt.request_digest != digest:
                    raise ProjectError(409, "Resume request ID was already used for different input")
                return PipelineRunRead.model_validate(run)

        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            if result := await replay(session, run):
                return result
            check_revision(run, request.expected_revision)
            if request.decision != "revoke" and run.state not in ("paused", "blocked"):
                raise ProjectError(409, "Inspect the current wait before submitting a decision")
            project = await self.projects.get(session, run.project_id)
            if not project.enabled or (project.github_repository, project.github_connector_id) != (
                run.github_repository,
                run.github_connector_id,
            ):
                raise ProjectError(409, "Project disabled or GitHub binding changed")
            response = await RunInteractionService().response_for_resume(session, run, request.answer_id)
            if request.decision and response:
                raise ProjectError(422, "Apply the direction answer separately from integration approval")
            previous, snapshot = dict(run.specrig_progress or {}), dict(run.specrig_snapshot)
            project_revision = project.revision
            connector, repository, number = project.github_connector_id, project.github_repository, run.pull_number
        evidence = dict(previous)
        pull = None
        if request.decision not in ("revoke", "reject"):
            pull = await self.observer.get_pull_request(connector, repository, number)
            if pull.get("state") != "open":
                raise ProjectError(409, "Pull request is no longer open")
            token = await self.observer.get_token(connector, "github")
            evidence = await SpecrigService().inspect(repository, snapshot["spec_dir"], pull, token, snapshot=snapshot)
            if request.decision == "approve" and (
                previous.get("rework_head") == evidence["head_sha"]
                or not approval_gate(evidence)
                or evidence["evidence_digest"] != previous.get("evidence_digest")
            ):
                raise ProjectError(409, "Approval evidence changed; resume inspection before approving")
            if response and response[0].head_sha != evidence["head_sha"]:
                raise ProjectError(409, "PR changed since the question; dismiss the stale question first")
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            if result := await replay(session, run):
                return result
            check_revision(run, request.expected_revision)
            project = await self.projects.get(session, run.project_id)
            if not project.enabled or project.revision != project_revision:
                raise ProjectError(409, "Project changed during decision")
            response = await RunInteractionService().response_for_resume(session, run, request.answer_id)
            now = get_current_utc_time()
            attempt = None
            if request.decision == "approve":
                evidence["approval"] = {
                    "actor": actor,
                    "head_sha": evidence["head_sha"],
                    "evidence_digest": evidence["evidence_digest"],
                    "saw_ready": not (pull or {}).get("draft", False),
                    "revision": run.revision,
                }
                run.state, run.pause_reason = "implementing", None
            elif request.decision in ("reject", "revoke"):
                evidence.pop("approval", None)
                evidence["integrated"] = False
                run.state = "canceled" if request.decision == "reject" else "blocked"
                run.pause_reason = f"Integration {request.decision} by {actor}: {request.feedback or ''}"
            elif request.decision == "revise" or response:
                feedback = (request.feedback or "") if not response else response[1].answer
                if not feedback.strip():
                    raise ProjectError(422, "Describe the requested change")
                evidence.pop("approval", None)
                evidence["rework_head"] = evidence["head_sha"]
                run.specrig_progress = evidence
                run.epoch += 1
                attempt = await SpecrigProgress(self.repo).dispatch(session, run, evidence, now, feedback)
                if response and attempt:
                    response[0].state, response[1].applied_attempt_id = "applied", attempt.id
            else:
                # Generic resume only re-inspects; it never grants approval.
                run.state, run.pause_reason = "implementing", None
                run.epoch += 1
            if request.decision == "reject":
                active = await self.repo.active_attempt(session, run.id)
                if active:
                    active.state, active.finished_at = "failed", now
                    active.failure_code = "INTEGRATION_REJECTED"
            run.specrig_progress = evidence
            run.project_revision = project_revision
            run.lease_owner = run.lease_token = run.lease_expires_at = None
            run.next_action_at = None
            run.revision += 1
            session.add(
                RunResumeReceipt(
                    id=request.request_id,
                    pipeline_run_id=run.id,
                    request_digest=digest,
                    decision_evidence={
                        "actor": actor,
                        "action": request.decision or "resume",
                        "revision": request.expected_revision,
                        "head_sha": evidence.get("head_sha"),
                        "base_sha": evidence.get("base_sha"),
                        "evidence_digest": evidence.get("evidence_digest"),
                        "feedback": request.feedback,
                        "prior_approval": previous.get("approval"),
                    },
                    execution_attempt_id=attempt.id if attempt else None,
                )
            )
            await session.flush()
            return PipelineRunRead.model_validate(run)
