"""Explicit operator reconciliation, without retrying uncertain provider creation."""

from app.features.project_management.connection_tests.adapters.registry import find_adapter
from app.features.project_management.connection_tests.models import ACTIVE, ConnectionTest
from app.features.project_management.connection_tests.ownership import candidate_heads, confirmed
from app.features.project_management.connection_tests.schemas import ResolveCleanup
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.utils.time_util import get_current_utc_time


def can_resolve(row: ConnectionTest) -> bool:
    snapshot = row.catalog_snapshot or {}
    adapter = find_adapter(snapshot.get("kind", ""), snapshot.get("adapter", ""))
    return bool(
        adapter
        and adapter.spec.manual_cleanup_resolution
        and row.status != ACTIVE
        and row.cleanup_status != "completed"
        and (row.evidence.get("output_discovery_pending") or row.evidence.get("unconfirmed_pulls"))
    )


def resolve(row: ConnectionTest, request: ResolveCleanup) -> None:
    now = get_current_utc_time()
    if row.lease_until and as_utc(row.lease_until) > now:
        raise ProjectError(409, "A test step is in progress; refresh and retry after it finishes")
    for previous in row.evidence.get("cleanup_resolutions", []):
        if previous["request_id"] == str(request.request_id):
            if previous["note"] != request.note or previous["unrelated_pulls"] != request.unrelated_pulls:
                raise ProjectError(409, "This resolution request ID was already used with different details")
            return
    if not can_resolve(row):
        raise ProjectError(409, "Only terminal tests with unresolved cleanup can be reviewed")
    if candidate_heads(row) != request.unrelated_pulls:
        raise ProjectError(409, "PR evidence changed; refresh and review the current candidates")
    if any(confirmed(row, number) for number in request.unrelated_pulls):
        raise ProjectError(409, "Confirmed test PRs cannot be dismissed as unrelated work")
    resolution = {
        **request.model_dump(mode="json"),
        "resolved_at": now.isoformat(),
    }
    evidence = {**row.evidence}
    evidence["cleanup_resolutions"] = [*evidence.get("cleanup_resolutions", []), resolution]
    # Keep prior reviewed heads so a later candidate does not require re-reviewing unchanged PRs.
    unrelated = {**evidence.get("cleanup_resolution", {}).get("unrelated_pulls", {}), **request.unrelated_pulls}
    evidence["cleanup_resolution"] = {**resolution, "unrelated_pulls": unrelated}
    evidence["unconfirmed_pulls"] = {}
    evidence["owned_pulls"] = {
        number: pull
        for number, pull in evidence.get("owned_pulls", {}).items()
        if number not in request.unrelated_pulls
    }
    if str(evidence.get("pull_number")) in request.unrelated_pulls:
        for key in ("pull_number", "pull_url", "output_branch"):
            evidence.pop(key, None)
    evidence.pop("cleanup_warning", None)
    # A new bounded GitHub scan still runs before protection is released or branches are deleted.
    evidence["output_discovery_pending"] = True
    row.evidence = evidence
    row.lease_token = row.lease_until = None
