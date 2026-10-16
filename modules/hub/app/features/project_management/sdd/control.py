"""Typed decisions reuse PipelineRun locking, questions and durable resume receipts."""

from app.features.project_management.pipeline_runs.interaction_service import RunInteractionService, check_revision
from app.features.project_management.pipeline_runs.models import RunResumeReceipt
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time

from .decisions import validate_answer
from .gates import INTEGRATION_REQUEST
from .progress import SddProgress, approval_gate, carry_decisions
from .services import SddService


class SddControl:
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
            if run.sdd_snapshot.get("provider") != "devkit-spec":
                raise ProjectError(409, "Legacy execution is read-only; enroll a new SDD run")
            if request.decision != "revoke" and run.state not in ("paused", "blocked"):
                raise ProjectError(409, "Inspect the current wait before submitting a decision")
            project = await self.projects.get(session, run.project_id)
            if not project.enabled or (project.github_repository, project.github_connector_id) != (
                run.github_repository,
                run.github_connector_id,
            ):
                raise ProjectError(409, "Project disabled or GitHub binding changed")
            response = await RunInteractionService().response_for_resume(session, run, request.answer_id)
            if sum(bool(x) for x in (request.decision, response, request.workflow_answer)) > 1:
                raise ProjectError(422, "Apply the direction answer separately from integration approval")
            previous, snapshot = dict(run.sdd_progress or {}), dict(run.sdd_snapshot)
            project_revision = project.revision
            connector, repository, number = project.github_connector_id, project.github_repository, run.pull_number
        evidence = dict(previous)
        pull = None
        if request.decision not in ("revoke", "reject"):
            pull = await self.observer.get_pull_request(connector, repository, number)
            if pull.get("state") != "open":
                raise ProjectError(409, "Pull request is no longer open")
            token = await self.observer.get_token(connector, "github")
            evidence = await SddService().inspect(repository, snapshot["spec_dir"], pull, token, snapshot=snapshot)
            carry_decisions(previous, evidence)
            evidence["pr_draft"] = bool(pull.get("draft"))
            if request.decision == "approve" and (
                previous.get("rework_head") == evidence["head_sha"]
                or not approval_gate(evidence)
                or evidence["evidence_digest"] != previous.get("evidence_digest")
            ):
                raise ProjectError(409, "Approval evidence changed; resume inspection before approving")
            operation = None
            if request.workflow_answer:
                if evidence["evidence_digest"] != previous.get("evidence_digest"):
                    raise ProjectError(409, "Workflow evidence changed; inspect again before answering")
                validate_answer(evidence, request.workflow_answer.model_dump())
                operation = request.workflow_answer.model_dump()
            elif request.decision == "approve" and any(
                r["id"] == INTEGRATION_REQUEST and r.get("answer", "record") == "record"
                for r in evidence["current"].get("requests", [])
            ):
                # A record-channel integration gate gets a decision record; the given channel (the devkit-spec
                # workflows) is satisfied by --given on the approved basis and never recorded.
                operation = {"request": INTEGRATION_REQUEST, "action": "accept"}
            elif request.decision == "revise":
                stages = [s["id"] for s in evidence["workflow"].get("stages", [])]
                current_id = (evidence["current"].get("stage") or {}).get("id")
                earlier = stages[: stages.index(current_id) + 1] if current_id in stages else []
                target = next((name for name in ("build-verify", "review-refine", current_id) if name in earlier), None)
                if target:
                    operation = {"return_to": target}
            if operation:
                operation.update(
                    id=str(request.request_id),
                    actor=actor,
                    note=request.feedback,
                    expected_digest=evidence["evidence_digest"],
                )
                prepared = await SddService().inspect(
                    repository, snapshot["spec_dir"], pull, token, snapshot=snapshot, operation=operation
                )
                if prepared.get("prepared_record"):
                    evidence["decision_records"] = [*evidence.get("decision_records", []), prepared["prepared_record"]]
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
            if request.workflow_answer:
                transitions = [
                    r["authorized_workflow"]
                    for r in evidence.get("decision_records", [])
                    if r.get("authorized_workflow")
                ]
                if transitions:
                    run.sdd_snapshot = {**run.sdd_snapshot, "authorized_workflows": transitions}
                evidence.pop("approval", None)
                evidence["decision_head"] = evidence["head_sha"]
                run.epoch += 1
                run.sdd_progress = evidence
                # Even decline/cancel records are published; the runner stops at the still-open request.
                attempt = await SddProgress(self.repo).dispatch(
                    session,
                    run,
                    evidence,
                    now,
                    "Publish the recorded workflow answer. Continue only if devkit reports no human request.",
                )
            elif request.decision == "approve":
                evidence.pop("approval_withheld", None)
                evidence["approval"] = {
                    "actor": actor,
                    "source": "hub",
                    "head_sha": evidence["head_sha"],
                    "evidence_digest": evidence["evidence_digest"],
                    "saw_ready": not (pull or {}).get("draft", False),
                    "revision": run.revision,
                }
                run.state, run.pause_reason = "implementing", None
            elif request.decision in ("reject", "revoke"):
                evidence.pop("approval", None)
                evidence["integrated"] = False
                evidence["approval_withheld"] = True
                run.state = "canceled" if request.decision == "reject" else "blocked"
                run.pause_reason = f"Integration {request.decision} by {actor}: {request.feedback or ''}"
            elif request.decision == "revise" or response:
                feedback = (
                    (request.feedback or "")
                    if not response
                    else (f"Question: {response[0].question}\nAnswer by {response[1].actor}: {response[1].answer}")
                )
                if not feedback.strip():
                    raise ProjectError(422, "Describe the requested change")
                evidence.pop("approval", None)
                if request.decision == "revise" or previous.get("approval") or approval_gate(evidence):
                    evidence["approval_withheld"] = True
                if request.decision == "revise":
                    evidence["rework_head"] = evidence["head_sha"]
                run.sdd_progress = evidence
                run.epoch += 1
                attempt = await SddProgress(self.repo).dispatch(session, run, evidence, now, feedback)
                if response and attempt:
                    response[0].state, response[1].applied_attempt_id = "applied", attempt.id
            else:
                # Generic resume only re-inspects; it never grants approval.
                run.state, run.pause_reason = "implementing", None
                run.epoch += 1
                if not evidence.get("lint_blocked") and (
                    evidence.get("rework_head") == evidence["head_sha"]
                    or not (evidence.get("current", {}).get("stage") or {}).get("human_gate")
                ):
                    run.sdd_progress = evidence
                    attempt = await SddProgress(self.repo).dispatch(session, run, evidence, now)
            if request.decision == "reject":
                active = await self.repo.active_attempt(session, run.id)
                if active:
                    active.state, active.finished_at = "failed", now
                    active.failure_code = "INTEGRATION_REJECTED"
            evidence.pop("waiting_for_approval", None)
            run.sdd_progress = evidence
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
                        "action": request.decision
                        or (request.workflow_answer.action if request.workflow_answer else "resume"),
                        "workflow_answer": request.workflow_answer.model_dump() if request.workflow_answer else None,
                        "decision_records": evidence.get("decision_records", []),
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
