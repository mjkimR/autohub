"""Native stage transitions under the existing PipelineRun lease and transaction."""

from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from app.features.project_management.pipeline_runs.interaction_service import RunInteractionService
from app.features.project_management.pipeline_runs.models import ExecutionAttempt, RunResumeReceipt
from app.features.project_management.pipeline_runs.requests import build_implementation_request, request_digest
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc, finish_closed_pull
from app.features.project_management.projects.errors import ProjectError

from .decisions import publication_instructions
from .services import SddService


def approval_gate(evidence):
    stage = evidence.get("current", {}).get("stage") or {}
    passed_integration = any(
        item.get("human_gate") == "integration" and item["id"] in evidence.get("current", {}).get("done", [])
        for item in evidence.get("workflow", {}).get("stages", [])
    )
    return stage.get("human_gate") == "integration" or (not evidence.get("approval") and passed_integration)


def merge_ready(evidence):
    stage = evidence.get("current", {}).get("stage") or {}
    return evidence.get("integrated") and "merged" in stage.get("exit", [])


def carry_decisions(previous, evidence):
    # CLI output cannot erase an operator's request or restore revoked authorization.
    for key in ("rework_head", "approval_withheld", "decision_records", "decision_head"):
        if key in previous:
            evidence[key] = previous[key]
    return evidence


class SddProgress:
    def __init__(self, repo):
        self.repo = repo

    async def observe(self, snapshot, previous, target, pull, observer):
        if pull.get("state") == "closed":
            return {"pull": pull}
        approval = previous.get("approval")
        if approval and approval.get("saw_ready") and pull.get("draft"):
            return {"pull": pull, "error": "Integration approval revoked: PR returned to draft", "revoke": True}
        if approval and pull["head"]["sha"] != previous.get("head_sha") and not previous.get("allow_head_change"):
            return {
                "pull": pull,
                "error": "PR head changed outside a delivered integration or fix; inspect and approve again",
                "revoke": True,
            }
        try:
            token = await observer.get_token(target.connector_id, "github")
            evidence = await SddService().inspect(
                target.repository, snapshot["spec_dir"], pull, token, snapshot=snapshot, approved=bool(approval)
            )
            carry_decisions(previous, evidence)
            evidence["pr_draft"] = bool(pull.get("draft"))
            if approval:
                evidence["approval"] = {
                    **approval,
                    "saw_ready": approval.get("saw_ready", False) or not pull.get("draft", False),
                }
            return {"pull": pull, "evidence": evidence}
        except ProjectError as exc:
            return {"pull": pull, "error": str(exc)}

    async def dispatch(self, session, run, evidence, now, feedback=""):
        stage = evidence.get("current", {}).get("stage") or {}
        stage_id = stage.get("id", "inspect")
        attempts = await self.repo.list_attempts(session, run.id)
        visits = [
            a
            for a in attempts
            if a.epoch == run.epoch
            and a.request_snapshot.get("sdd_stage") == stage_id
            and a.request_snapshot.get("sdd_base_sha") == evidence["base_sha"]
        ]
        if len(visits) >= 3:
            run.state, run.pause_reason = (
                "blocked",
                f"SDD stage {stage_id} exceeded three attempts; inspect and resume",
            )
            return
        active = await self.repo.active_attempt(session, run.id)
        if active:
            active.state, active.finished_at = "completed", now
        request, _, key = build_implementation_request(run, run.github_repository or "")
        request.instructions += publication_instructions(evidence)
        request.instructions += await RunInteractionService().applied_context(session, run.id)
        request.pull_request.head_sha = evidence["head_sha"]
        request.instructions += (
            f"\nRequested stage: {stage_id}. Skills: {', '.join(stage.get('skills') or [])}. "
            f"Inspected base commit: {evidence['base_sha']}."
        )
        if evidence.get("approval"):
            request.instructions += (
                f"\nHub integration authorization: {evidence['approval']['actor']}; "
                f"approved head {evidence['approval']['head_sha']}. "
                "Use spec-integrate within the approved intent; reverify changed parts and reconcile. "
                "You may supply --given integration on that recorded basis. Stop before merge."
            )
        if feedback:
            request.instructions += f"\nOperator feedback: {feedback}\nRevisit affected implementation and review before requesting approval."
        payload = request.model_dump(mode="json")
        payload["sdd_stage"] = stage_id
        payload["sdd_base_sha"] = evidence["base_sha"]
        attempt = await self.repo.create_attempt(
            session,
            ExecutionAttempt(
                pipeline_run_id=run.id,
                attempt_number=await self.repo.next_attempt_number(session, run.id),
                epoch=run.epoch,
                kind="implementation",
                state="planned",
                request_snapshot=payload,
                request_digest=request_digest(payload),
                idempotency_key=key,
            ),
        )
        run.state, run.pause_reason, run.next_action_at = "dispatching", None, None
        return attempt

    async def apply(self, session, run, now, observed):
        original_state = run.state
        pull = observed["pull"]
        if pull.get("state") == "closed":
            await finish_closed_pull(self.repo, session, run, pull, now)
        elif observed.get("error"):
            progress = dict(run.sdd_progress or {})
            progress["error"] = observed["error"]
            if observed.get("revoke"):
                progress.pop("approval", None)
                progress["integrated"] = False
                progress["approval_withheld"] = True
            progress.pop("waiting_for_approval", None)
            run.sdd_progress = progress
            run.state, run.pause_reason = "blocked", observed["error"]
            run.revision += 1
        else:
            evidence = observed["evidence"]
            previous = run.sdd_progress or {}
            run.sdd_progress = evidence
            if (
                evidence.get("rework_head") == evidence["head_sha"]
                or evidence.get("decision_head") == evidence["head_sha"]
            ):
                active = await self.repo.active_attempt(session, run.id)
                expired = active and active.started_at and now - as_utc(active.started_at) > timedelta(minutes=45)
                run.state = "blocked" if expired else "implementing"
                run.pause_reason = (
                    "Requested changes have not completed within 45 minutes; inspect and resume"
                    if expired
                    else "Waiting for requested changes or decision publication and renewed evidence"
                )
                if expired:
                    run.revision += 1
            elif approval_gate(evidence):
                policy_auto = (
                    run.sdd_snapshot["policy"].get("approvals", {}).get("integration", {}).get("policy") == "auto"
                )
                ready = pull.get("draft") is False
                if not evidence.get("approval_withheld") and (policy_auto or ready):
                    actor = "github:pr-ready" if ready else "policy:workflow.approvals.integration=auto"
                    evidence["approval"] = {
                        "actor": actor,
                        "source": "pr-ready" if ready else "policy",
                        "observed_at": now.isoformat(),
                        "head_sha": evidence["head_sha"],
                        "evidence_digest": evidence["evidence_digest"],
                        "saw_ready": not pull.get("draft", False),
                    }
                    session.add(
                        RunResumeReceipt(
                            id=uuid5(
                                NAMESPACE_URL, f"sdd-approval:{run.id}:{run.revision}:{evidence['evidence_digest']}"
                            ),
                            pipeline_run_id=run.id,
                            request_digest=request_digest(evidence["approval"]),
                            decision_evidence={
                                **evidence["approval"],
                                "action": "approve",
                                "revision": run.revision,
                                "base_sha": evidence["base_sha"],
                            },
                        )
                    )
                    run.sdd_progress = dict(evidence)
                    run.state, run.pause_reason = "implementing", None
                else:
                    evidence["waiting_for_approval"] = not evidence.get("approval_withheld", False)
                    run.state, run.pause_reason = (
                        "paused",
                        "G3: inspect the final report and approve, request changes, or reject",
                    )
                if previous != evidence or run.state != original_state:
                    run.revision += 1
            elif merge_ready(evidence) and evidence.get("approval"):
                run.state, run.pause_reason = "awaiting_ci", None
                if previous != evidence:
                    run.revision += 1
            else:
                active = await self.repo.active_attempt(session, run.id)
                stage = evidence["current"].get("stage") or {}
                requested_stage = active.request_snapshot.get("sdd_stage") if active else None
                if evidence["current"].get("requests") or stage.get("human_gate"):
                    run.state, run.pause_reason = (
                        "blocked",
                        f"Direction decision required: {stage.get('name', 'workflow gate')}",
                    )
                    run.revision += 1
                elif (
                    not active
                    or requested_stage != stage.get("id")
                    or previous.get("head_sha") != evidence["head_sha"]
                    or previous.get("base_sha") != evidence["base_sha"]
                ):
                    await self.dispatch(session, run, evidence, now)
                    run.revision += 1
                elif active.started_at and now - as_utc(active.started_at) > timedelta(minutes=45):
                    run.state, run.pause_reason = (
                        "blocked",
                        "SDD stage has not completed within 45 minutes; inspect and resume",
                    )
                    run.revision += 1
        run.next_action_at = (
            now + timedelta(minutes=5) if (run.sdd_progress or {}).get("waiting_for_approval") else None
        )
        await session.flush()
        return PipelineRunRead.model_validate(run)
