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
    if run.specrig_snapshot:
        progress = run.specrig_progress or {}
        stage = progress.get("current", {}).get("stage") or {}
        instructions += (
            f"\nSpecrig spec: {run.specrig_snapshot['spec_dir']}. "
            f"Current workflow stage: {stage.get('id', 'inspect')}. "
            "Read config show and workflow show/next/checks. Execute only the current stage using its skills; "
            "publish its evidence and stop for the hub to evaluate the next stage. "
            "Do not declare approval-given, lint-ci-clean or merged without hub evidence. "
            "Do not mark the PR ready or merge. Ask for direction through the existing question channel. "
            "Intermediate commits may use specrig commit --development; final lint must omit --development."
        )
    snapshot = ImplementationRequest(
        specrig_stage=((run.specrig_progress or {}).get("current", {}).get("stage") or {}).get("id")
        if run.specrig_snapshot
        else None,
        specrig_base_sha=(run.specrig_progress or {}).get("base_sha") if run.specrig_snapshot else None,
        correlation_marker=f"hub-attempt:{idempotency_key}",
        repository=repository,
        pull_request=pull,
        instructions=instructions,
    )
    return snapshot, request_digest(snapshot.model_dump(mode="json")), idempotency_key
