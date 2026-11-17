"""Decision-inbox rows carry the SDD activity identity their owning Run retained."""

import pytest
from app.features.project_management.pipeline_runs.discovery_service import sdd_identity
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.requests import build_implementation_request

SDD = {"provider": "repository-agent"}
PULL = {
    "number": 7,
    "url": "https://github.com/owner/repo/pull/7",
    "title": "Plan",
    "base_ref": "main",
    "head_ref": "plan-a",
    "head_sha": "a" * 40,
}


@pytest.mark.parametrize(
    ("snapshot", "identity"),
    [
        (None, (None, None)),
        ({}, (None, None)),
        ({**SDD, "spec_dir": "docs/proposals/PROP-a", "activity_kind": "plan"}, ("plan", "docs/proposals/PROP-a")),
        ({**SDD, "spec_dir": "specs/0001-a", "activity_kind": "dev"}, ("dev", "specs/0001-a")),
        # A snapshot without an activity kind requests Development, as its implementation request does.
        ({**SDD, "spec_dir": "docs/proposals/PROP-a"}, ("dev", "docs/proposals/PROP-a")),
        # An unrecognized kind is reported unknown, never inferred.
        ({**SDD, "spec_dir": "specs/0001-a", "activity_kind": "review"}, (None, "specs/0001-a")),
        ({**SDD, "spec_dir": "", "activity_kind": "review"}, (None, None)),
        ({**SDD, "activity_kind": "plan"}, (None, None)),
        # Without the repository-agent provider the snapshot is not an SDD activity: no default kind.
        ({"spec_dir": "docs/proposals/PROP-a"}, (None, "docs/proposals/PROP-a")),
    ],
)
def test_identity_comes_from_the_retained_snapshot(snapshot, identity):
    assert sdd_identity(PipelineRun(sdd_snapshot=snapshot)) == identity


def test_missing_kind_matches_the_requested_activity():
    snapshot = {**SDD, "spec_dir": "docs/proposals/PROP-a"}
    run = PipelineRun(sdd_snapshot=snapshot, pull_snapshot=PULL)
    request, _, _ = build_implementation_request(run, "owner/repo")
    activity, _ = sdd_identity(run)
    assert f"Requested repository activity: {activity}." in request.instructions
