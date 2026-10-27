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
from .evidence import in_context
from .gates import INTEGRATION_GATE, PLAN_ACCEPT_REQUEST
from .services import SddService
from .units import is_proposal, proposal_slug

# What an agent is told about a warning. The human remediation of RECEIPT_STALE (commit a new receipt) would end
# this run's contract mid-flight, so the agent is told to leave it to the operator instead.
AGENT_NOTES = {
    "RECEIPT_STALE": (
        "Hub evaluates this pull request with its reviewed runtime because the committed devkit receipt differs "
        "from it. Do not change .devkit/ in this run; that ends the run's contract. The operator re-enrolls after "
        "aligning the receipt."
    )
}


def hold_of(evidence):
    return evidence.get("hold") or {}


def reviewed(evidence):
    """The Planning worker left a completed worker envelope: the proposal is ready for plan-accept."""
    context = evidence.get("report_context")
    workers = [
        r
        for r in evidence.get("reports") or []
        if r.get("kind") == "worker" and (not context or in_context(r, context))
    ]
    return bool(workers) and max(workers, key=lambda r: r.get("seq") or 0).get("status") == "completed"


def completed_plan(evidence):
    return (
        is_proposal((evidence.get("snapshot") or {}).get("spec_dir", ""))
        and evidence.get("unit_status") in ("reviewing", "accepted")
        and evidence.get("current", {}).get("complete")
        and reviewed(evidence)
        and not held(evidence)
    )


def delegated_plan(evidence):
    return all(
        policy.get("approvals", {}).get("plan-accept", {}).get("policy") == "auto"
        for policy in ((evidence.get("snapshot") or {}).get("policy") or {}, evidence.get("base_policy") or {})
    )


def awaiting_review(evidence):
    """A proposal asked for plan-accept before any Planning worker ran: dispatch the worker, do not ask yet."""
    unit = str((evidence.get("snapshot") or {}).get("spec_dir") or "")
    requests = (evidence.get("current") or {}).get("requests") or []
    return is_proposal(unit) and any(r.get("id") == PLAN_ACCEPT_REQUEST for r in requests) and not reviewed(evidence)


def plan_approval(plan):
    from .plan_decisions import plan_approval as build

    return build(plan)


def held(evidence):
    """An unresolved worker problem or an unanswered question: no gate passes and nothing is merged."""
    hold = hold_of(evidence)
    return bool(hold.get("blocked") or hold.get("pending_questions"))


def hold_reason(hold):
    problems = [f"{p.get('file')}: {p.get('cause')}" for p in hold.get("problems") or []]
    malformed = [f"{m.get('file')}: malformed worker envelope" for m in hold.get("malformed_workers") or []]
    return (
        "Worker problem unresolved: " + "; ".join([*problems, *malformed])[:900]
    ) + ". A resolution envelope written by whoever fixed it clears the hold."


def request_reason(evidence, stage):
    questions = [r for r in evidence.get("current", {}).get("requests", []) if r.get("answer") == "envelope"]
    if questions:
        return "Worker question pending: " + "; ".join(str(q.get("title") or q.get("id")) for q in questions)[:900]
    return f"Direction decision required: {stage.get('name', 'workflow gate')}"


def approval_gate(evidence):
    if held(evidence):
        return False
    if plan := evidence.get("plan_decision"):
        return evidence.get("head_sha") == plan.get("commit_sha")
    if evidence.get("approval_withheld") and completed_plan(evidence) and delegated_plan(evidence):
        return True  # Explicit Hub reapproval restores a previously withdrawn policy delegation.
    stage = evidence.get("current", {}).get("stage") or {}
    passed_integration = any(
        item.get("human_gate") == INTEGRATION_GATE and item["id"] in evidence.get("current", {}).get("done", [])
        for item in evidence.get("workflow", {}).get("stages", [])
    )
    return stage.get("human_gate") == INTEGRATION_GATE or (not evidence.get("approval") and passed_integration)


def merge_ready(evidence):
    if held(evidence) or evidence.get("approval_withheld"):
        return False
    if plan := evidence.get("plan_decision"):
        # A decided proposal merges on the commit that carries the decision; its workflow has no merge check.
        return evidence.get("head_sha") == plan.get("commit_sha")
    stage = evidence.get("current", {}).get("stage") or {}
    return bool(evidence.get("integrated")) and "merged" in stage.get("exit", [])


def carry_decisions(previous, evidence):
    # CLI output cannot erase an operator's request or restore revoked authorization.
    for key in (
        "rework_head",
        "approval_withheld",
        "decision_records",
        "decision_head",
        "plan_decision",
        "allow_head_change",
    ):
        if key in previous:
            evidence[key] = previous[key]
    return evidence


class SddProgress:
    def __init__(self, repo, projects=None):
        self.repo, self.projects = repo, projects

    async def observe(self, snapshot, previous, target, pull, observer, *, run_id=None, revision=None, lease=None):
        if pull.get("state") == "closed":
            return {"pull": pull}
        approval = previous.get("approval")
        if approval and approval.get("saw_ready") and pull.get("draft"):
            return {"pull": pull, "error": "Integration approval revoked: PR returned to draft", "revoke": True}
        plan = previous.get("plan_decision") or {}
        published_head = (
            approval
            and not previous.get("approval_withheld")
            and approval.get("head_sha") == plan.get("commit_sha") == pull["head"]["sha"]
            and plan.get("head_sha") == previous.get("head_sha")
        )
        if (
            approval
            and pull["head"]["sha"] != previous.get("head_sha")
            and not (published_head or previous.get("allow_head_change"))
        ):
            return {
                "pull": pull,
                "error": "PR head changed outside a delivered integration or fix; inspect and approve again",
                "revoke": True,
            }
        publication_request_id = None
        try:
            token = await observer.get_token(target.connector_id, "github")
            evidence = await SddService().inspect(
                target.repository, snapshot["spec_dir"], pull, token, snapshot=snapshot, approved=bool(approval)
            )
            if (previous.get("plan_decision") or {}).get("authority") == "policy" and evidence.get(
                "base_policy", {}
            ).get("approvals", {}).get("plan-accept", {}).get("policy") != "auto":
                return {
                    "pull": pull,
                    "error": "Owning-base plan-accept delegation changed; enroll again",
                    "revoke": True,
                }
            if run_id is not None:
                assert revision is not None
                from app.features.project_management.pipeline_runs.interaction_schemas import ResumeRunRequest

                from .plan_publication import PlanDecisionPublisher

                publisher = PlanDecisionPublisher(self.repo, self.projects, observer)
                if recovered := await publisher.recover(run_id, pull, preserve_lease=True, lease=lease):
                    return {"published_run": recovered}
                candidate = (
                    completed_plan(evidence)
                    and not snapshot.get("handoff_pending")
                    and pull["head"].get("ref") == f"plan-{proposal_slug(evidence['snapshot']['spec_dir'])}"
                    and not previous.get("plan_decision")
                    and not any(previous.get(key) == evidence["head_sha"] for key in ("rework_head", "decision_head"))
                )
                if candidate:
                    policy = evidence["snapshot"]["policy"].get("approvals", {}).get("plan-accept", {}).get("policy")
                    base_policy = (
                        evidence.get("base_policy", {}).get("approvals", {}).get("plan-accept", {}).get("policy")
                    )
                    if policy == "auto" and base_policy == "auto" and previous.get("approval_withheld"):
                        evidence["waiting_for_plan_approval"] = True
                    elif policy == "auto" and base_policy == "auto":
                        request = ResumeRunRequest(
                            request_id=uuid5(
                                NAMESPACE_URL,
                                f"sdd-plan-accept:{run_id}:{revision}:{evidence['head_sha']}:{evidence['base_sha']}",
                            ),
                            expected_revision=revision,
                            decision="accept_plan",
                            head_sha=evidence["head_sha"],
                            feedback="Planning completed under owning-base plan-accept=auto",
                        )
                        publication_request_id = request.request_id
                        result = await publisher.decide(
                            run_id,
                            request,
                            "policy:workflow.approvals.plan-accept=auto",
                            automatic=True,
                            inspected=evidence,
                            lease=lease,
                        )
                        return {"published_run": result}
                    elif policy == "auto":
                        return {
                            "pull": pull,
                            "error": "The owning base does not delegate plan-accept; align policy and enroll again",
                        }
            carry_decisions(previous, evidence)
            evidence["pr_draft"] = bool(pull.get("draft"))
            if approval:
                evidence["approval"] = {
                    **approval,
                    "saw_ready": approval.get("saw_ready", False) or not pull.get("draft", False),
                }
            return {"pull": pull, "evidence": evidence}
        except ProjectError as exc:
            return {"pull": pull, "error": str(exc), "publication_request_id": publication_request_id}

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
        for warning in evidence.get("warnings") or []:
            note = AGENT_NOTES.get(str(warning.get("code")), warning.get("detail"))
            request.instructions += f"\nHub warning ({warning.get('code')}): {note}"
        unit = (run.sdd_snapshot or {}).get("spec_dir", "<unit>")
        for problem in hold_of(evidence).get("problems") or []:
            request.instructions += (
                f"\nUnresolved worker problem in {problem.get('file')}: {problem.get('cause')} "
                f"Recovery: {problem.get('recovery')} Once it is actually fixed, record it with "
                f"devkit workflow envelope resolution --unit {unit} --resolves {problem.get('file')} --summary <fix>; "
                "no gate passes until then."
            )
        if evidence.get("approval"):
            request.instructions += (
                f"\nHub integration authorization: {evidence['approval']['actor']}; "
                f"approved head {evidence['approval']['head_sha']}. "
                "Use spec-integrate within the approved intent; reverify changed parts and reconcile. "
                f"You may supply --given {INTEGRATION_GATE} on that recorded basis. Stop before merge."
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
            if request_id := observed.get("publication_request_id"):
                receipt = await session.get(RunResumeReceipt, request_id)
                data = dict(receipt.decision_evidence or {}) if receipt else {}
                publication = data.get("publication") or {}
                if (
                    receipt
                    and receipt.pipeline_run_id == run.id
                    and data.get("revision") == run.revision
                    and data.get("automatic")
                    and publication.get("state") == "uncertain"
                ):
                    # Only this error transition may extend the original authorization. User actions never do.
                    receipt.decision_evidence = {
                        **data,
                        "publication": {**publication, "recovery_revision": run.revision + 1},
                    }
            run.revision += 1
        else:
            evidence = observed["evidence"]
            previous = run.sdd_progress or {}
            if evidence.get("rebound"):
                # The handoff happened: the run's contract is the spec's from here (activity effort carries over).
                run.sdd_snapshot = {
                    **evidence["snapshot"],
                    **(
                        {"activity_effort": run.sdd_snapshot["activity_effort"]}
                        if run.sdd_snapshot.get("activity_effort")
                        else {}
                    ),
                }
            run.sdd_progress = evidence
            plan = evidence.get("plan_decision")
            if plan and evidence["head_sha"] == plan.get("commit_sha"):
                # Hub's own decision commit is the head now: merge it by policy, unless a worker problem holds.
                evidence["allow_head_change"] = False
                if held(evidence):
                    run.state, run.pause_reason = "blocked", hold_reason(hold_of(evidence))
                elif evidence.get("approval_withheld"):
                    run.state, run.pause_reason = (
                        "blocked",
                        "Proposal merge approval withdrawn; inspect and approve again",
                    )
                else:
                    evidence.setdefault("approval", plan_approval(plan))
                    run.state, run.pause_reason = "awaiting_ci", None
                if previous != evidence or run.state != original_state:
                    run.revision += 1
            elif (
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
                    run.sdd_snapshot["policy"].get("approvals", {}).get(INTEGRATION_GATE, {}).get("policy") == "auto"
                )
                ready = pull.get("draft") is False
                if not evidence.get("approval_withheld") and (policy_auto or ready):
                    actor = "github:pr-ready" if ready else f"policy:workflow.approvals.{INTEGRATION_GATE}=auto"
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
                        "plan-accept: explicit proposal reapproval is required"
                        if evidence.get("waiting_for_plan_approval")
                        else f"{INTEGRATION_GATE}: inspect the final report and approve, request changes, or reject",
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
                if hold_of(evidence).get("blocked"):
                    # Only a resolution envelope by whoever fixed the problem clears this; retries do not.
                    run.state, run.pause_reason = "blocked", hold_reason(hold_of(evidence))
                    if previous != evidence or run.state != original_state:
                        run.revision += 1
                elif evidence.get("lint_blocked"):
                    # The final lint cannot run against the committed receipt; no agent attempt can repair that.
                    run.state, run.pause_reason = "blocked", str(evidence.get("lint_diagnostic"))
                    if previous != evidence or run.state != original_state:
                        run.revision += 1
                elif (evidence["current"].get("requests") or stage.get("human_gate")) and not awaiting_review(evidence):
                    run.state, run.pause_reason = "blocked", request_reason(evidence, stage)
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
