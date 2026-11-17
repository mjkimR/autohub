"""Decision-inbox rows carry the SDD activity identity their owning Run retained."""

import pytest
from app.features.project_management.pipeline_runs.discovery_service import sdd_identity
from app.features.project_management.pipeline_runs.models import PipelineRun


@pytest.mark.parametrize(
    ("snapshot", "identity"),
    [
        (None, (None, None)),
        ({}, (None, None)),
        ({"spec_dir": "docs/proposals/PROP-a", "activity_kind": "plan"}, ("plan", "docs/proposals/PROP-a")),
        ({"spec_dir": "specs/0001-a", "activity_kind": "dev"}, ("dev", "specs/0001-a")),
        # Older snapshots have no activity kind; it is reported unknown, not inferred.
        ({"spec_dir": "docs/proposals/PROP-a"}, (None, "docs/proposals/PROP-a")),
        ({"spec_dir": "", "activity_kind": "review"}, (None, None)),
    ],
)
def test_identity_comes_from_the_retained_snapshot(snapshot, identity):
    assert sdd_identity(PipelineRun(sdd_snapshot=snapshot)) == identity
