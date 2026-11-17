from copy import deepcopy
from uuid import uuid4

import pytest
from app.features.project_management.pipeline_runs.adapters.capabilities import PIPELINE_DELIVERY_ADAPTERS
from app.features.project_management.pipeline_runs.adapters.registry import _ADAPTERS
from app.features.project_management.pipeline_runs.dispatch import build_codex_mention_comment
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.requests import build_implementation_request, request_digest


def test_digest_is_order_independent_but_preserves_nested_request_content():
    snapshot = {"repository": "owner/app", "pull_request": {"title": "Fix", "number": 7}, "instructions": "Run checks"}
    reordered = {"instructions": "Run checks", "pull_request": {"number": 7, "title": "Fix"}, "repository": "owner/app"}
    assert request_digest(snapshot) == request_digest(reordered)
    changed = deepcopy(snapshot)
    changed["pull_request"]["number"] = 8
    assert request_digest(snapshot) != request_digest(changed)


def test_rebuilding_with_the_same_key_preserves_delivery_identity():
    run = PipelineRun(
        pull_snapshot={
            "number": 7,
            "url": "https://github.com/owner/app/pull/7",
            "title": "Fix",
            "base_ref": "main",
            "head_ref": "feature/7",
            "head_sha": "a" * 40,
        }
    )
    key = uuid4()
    request, digest, returned_key = build_implementation_request(run, "owner/app", idempotency_key=key)
    assert returned_key == key
    assert request.correlation_marker == f"hub-attempt:{key}"
    assert digest == request_digest(request.model_dump(mode="json"))
    assert build_implementation_request(run, "owner/app", idempotency_key=key) == (request, digest, key)
    assert build_implementation_request(run, "owner/app")[1] != digest


def test_advertised_delivery_capabilities_match_registered_implementations():
    assert set(_ADAPTERS) == PIPELINE_DELIVERY_ADAPTERS


def _run(sdd_snapshot: dict | None = None) -> PipelineRun:
    return PipelineRun(
        pull_snapshot={
            "number": 3,
            "url": "https://github.com/owner/app/pull/3",
            "title": "Planning: PROP-example",
            "base_ref": "main",
            "head_ref": "plan-example",
            "head_sha": "b" * 40,
        },
        sdd_snapshot=sdd_snapshot,
    )


GATE_OBLIGATIONS = (
    "human approval or decision gate",
    "first push the completed work, then raise the gate through the question marker",
    "a question raised after pushing completed work remains valid",
    # The parser binds the marker to the dispatched head; a pushed head would silently drop the gate.
    "keep the marker's attempt and head values exactly as given, even after you push",
    "short review summary",
    "accept, request changes (with the changes), or reject (with the reason)",
    "Never record or infer the operator's decision yourself before an answer arrives",
    "apply it as the operator's decision under the repository workflow",
    # Resume appends a generic "stop and ask again" suffix; a gate answer's changes stay in scope.
    "including requested changes to the reviewed work, which are within scope",
    "leave the PR Draft",
)


@pytest.mark.parametrize("activity", ["plan", "dev"])
def test_sdd_activity_instructions_raise_repository_gates_as_questions(activity):
    snapshot = {"provider": "repository-agent", "spec_dir": "docs/proposals/PROP-example", "activity_kind": activity}
    instructions = build_implementation_request(_run(snapshot), "owner/app")[0].instructions
    for obligation in GATE_OBLIGATIONS:
        assert obligation in instructions, obligation
    # Hub stays repository-neutral: no tool, gate ID or stage name.
    assert "devkit" not in instructions.lower() and "plan-accept" not in instructions


def test_ordinary_instructions_have_no_gate_text():
    instructions = build_implementation_request(_run(), "owner/app")[0].instructions
    assert instructions == (
        "Implement pull request #3 in owner/app on its branch plan-example. "
        "Follow the repository instructions, run the required checks, and push the result to that branch."
    )


def test_mention_comment_carries_the_gate_instruction_beside_the_question_marker():
    snapshot = {"provider": "repository-agent", "spec_dir": "docs/proposals/PROP-example", "activity_kind": "plan"}
    comment = build_codex_mention_comment(build_implementation_request(_run(snapshot), "owner/app")[0])
    gate = comment.index("raise the gate through the question marker")
    assert "a question raised after pushing completed work remains valid" in comment
    assert gate < comment.index("<!-- autohub-question ")
