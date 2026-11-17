"""Immutable implementation request construction and canonical identity."""

import json
from hashlib import sha256
from uuid import UUID, uuid4

from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.schemas import ImplementationRequest, PullRequestSnapshot

# Repository-neutral: Hub relays the operator's decision but never names or evaluates a workflow gate
# (CAP-SDD-native-delivery, ADR-repository-owned-sdd-execution).
SDD_GATE_INSTRUCTIONS = (
    "If the repository workflow stops at a human approval or decision gate (for example, accepting a reviewed plan), "
    "first push the completed work, then raise the gate through the question marker in your final reply. "
    "In this activity a question raised after pushing completed work remains valid; "
    "keep the marker's attempt and head values exactly as given, even after you push. "
    "The question must let the operator decide without opening another tool: state the decision requested, "
    "a short review summary (outcome, open questions, notable findings and checks) and the expected answers: "
    "accept, request changes (with the changes), or reject (with the reason). "
    "Never record or infer the operator's decision yourself before an answer arrives. "
    "When a resumed request carries an operator decision that answers such a gate, apply it as the operator's "
    "decision under the repository workflow, including requested changes to the reviewed work, which are within "
    "scope; ask again only when the answer is ambiguous. Then run the required checks, push the result and leave "
    "the PR Draft."
)


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
        intent = run.sdd_snapshot
        instructions += (
            f"\nRequested repository activity: {intent.get('activity_kind', 'dev')}. "
            f"SDD unit: {intent['spec_dir']}. "
            "The repository and its working agent own environment preparation, workflow interpretation "
            "and required repository checks. Follow its instructions through the requested work. "
            "Ask for missing direction through the existing question channel and stop when operator input is needed. "
            "Leave the PR Draft; the operator and Hub control ready status and merging."
            f"\n{SDD_GATE_INSTRUCTIONS}"
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
