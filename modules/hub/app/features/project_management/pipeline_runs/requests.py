"""Immutable implementation request construction and canonical identity."""

import json
from hashlib import sha256
from uuid import UUID, uuid4

from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.schemas import ImplementationRequest, PullRequestSnapshot


def request_digest(snapshot: dict) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode()).hexdigest()


def build_implementation_request(
    run: PipelineRun,
    repository: str,
    *,
    idempotency_key: UUID | None = None,
) -> tuple[ImplementationRequest, str, UUID]:
    idempotency_key = idempotency_key or uuid4()
    pull = PullRequestSnapshot.model_validate(run.pull_snapshot)
    instructions = (
        f"Implement pull request #{pull.number} in {repository} on its branch {pull.head_ref}. "
        "Follow the repository instructions, run the required checks, and push the result to that branch."
    )
    if run.sdd_snapshot:
        progress = run.sdd_progress or {}
        stage = progress.get("current", {}).get("stage") or {}
        instructions += (
            f"\nSdd spec: {run.sdd_snapshot['spec_dir']}. "
            f"Current workflow stage: {stage.get('id', 'inspect')}. "
            "Read devkit spec policy and devkit workflow show/next/checks --unit for this spec. Execute only the current stage using its skills; "
            "publish its evidence and stop for the hub to evaluate the next stage. "
            "Do not declare integration, lint-ci-clean or merged without hub evidence. "
            "Do not mark the PR ready or merge. Ask for direction through the existing question channel. "
            "Follow devkit gate and the repository commit policy. Final verification is devkit rules check --ci --base <base>."
        )
        unit = str(run.sdd_snapshot.get("spec_dir") or "")
        if run.sdd_snapshot.get("handoff_pending"):
            slug = unit.rsplit("PROP-", 1)[-1]
            instructions += (
                f"\nFirst step: devkit spec proposal handoff {slug} on this branch, then commit and push; the run follows "
                "the new spec bundle from its next stage. Before implementing, confirm the accepted proposal's premises "
                "still hold on the current base; a premise that no longer holds is a problem, never a change of the proposal."
            )
        elif unit.startswith("docs/proposals/"):
            instructions += (
                "\nPlanning worker: review the proposal as the planning-worker contract describes, set status reviewing "
                "if it is still draft, and leave exactly one worker envelope for this run (devkit workflow envelope "
                "worker --stage direction-handoff): needs_input with its questions when a person must decide, "
                "completed when the proposal is ready for plan-accept. Never set accepted or rejected: Hub records "
                "that decision. Stop after pushing."
            )
        if effort := run.sdd_snapshot.get("activity_effort"):
            instructions += (
                f"\nActivity effort: {effort}. It sets the review depth above the gates, exit checks and required "
                "policies, never below them; record it as activity_effort in the worker envelope."
            )
    snapshot = ImplementationRequest(
        sdd_stage=((run.sdd_progress or {}).get("current", {}).get("stage") or {}).get("id")
        if run.sdd_snapshot
        else None,
        sdd_base_sha=(run.sdd_progress or {}).get("base_sha") if run.sdd_snapshot else None,
        correlation_marker=f"hub-attempt:{idempotency_key}",
        repository=repository,
        pull_request=pull,
        instructions=instructions,
    )
    return snapshot, request_digest(snapshot.model_dump(mode="json")), idempotency_key
