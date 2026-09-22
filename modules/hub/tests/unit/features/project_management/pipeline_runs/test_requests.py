from copy import deepcopy
from uuid import uuid4

from app.features.project_management.pipeline_runs.adapters.capabilities import PIPELINE_DELIVERY_ADAPTERS
from app.features.project_management.pipeline_runs.adapters.registry import _ADAPTERS
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
