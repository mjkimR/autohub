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
