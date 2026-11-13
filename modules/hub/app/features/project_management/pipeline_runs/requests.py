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
        from app.features.project_management.sdd.execution import require_current

        require_current(run)
        intent = run.sdd_snapshot
        instructions += (
            f"\nRequested repository activity: {intent.get('activity_kind', 'dev')}. "
            f"SDD unit: {intent['spec_dir']}. "
            "The repository and its working agent own environment preparation, workflow interpretation "
            "and required repository checks. Follow its instructions through the requested work. "
            "Ask for missing direction through the existing question channel and stop when operator input is needed. "
            "Leave the PR Draft; the operator and Hub control ready status and merging."
        )
        if intent.get("handoff_pending"):
            instructions += " The requested Development activity starts from the named proposal; follow the repository's handoff instructions."
        if effort := intent.get("activity_effort"):
            instructions += f" Requested activity effort: {effort}."
    snapshot = ImplementationRequest(
        correlation_marker=f"hub-attempt:{idempotency_key}",
        repository=repository,
        pull_request=pull,
        instructions=instructions,
    )
    return snapshot, request_digest(snapshot.model_dump(mode="json")), idempotency_key
