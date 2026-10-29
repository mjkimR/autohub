import pytest
from app.features.project_management.sdd.evidence import reports, review_gaps
from app.features.project_management.sdd.progress import reviewed

pytestmark = pytest.mark.unit
CONTEXT = {"workflow": "sdd-proposal", "segment": 1}


def row(kind, seq=1, **kwargs):
    return {
        "kind": kind,
        "seq": seq,
        "file": f"envelopes/{kind}-{seq:02}.yaml",
        "status": "completed",
        **CONTEXT,
        **kwargs,
    }


def test_preserves_every_support_round_its_closing_review_and_actual_effort():
    rows = reports(
        {
            "envelopes": [
                row("worker", activity_effort="high", assumptions=["API stable"], unverified_areas=["Live provider"]),
                row("challenger", findings=[{"issue": "Boundary", "resolution": "open"}]),
                row("challenger", 2),
                row("scout"),
                row("ux-review", stage="spike", findings=[{"issue": "Empty state", "resolution": "open"}]),
                row("reverify", review="challenger-01.yaml"),
            ]
        }
    )
    assert {r["file"] for r in rows} == {
        f"envelopes/{name}"
        for name in (
            "worker-01.yaml",
            "challenger-01.yaml",
            "challenger-02.yaml",
            "scout-01.yaml",
            "ux-review-01.yaml",
            "reverify-01.yaml",
        )
    }
    ux = next(r for r in rows if r["kind"] == "ux-review")
    assert ux["stage"] == "spike" and ux["findings"] == [{"issue": "Empty state", "resolution": "open"}]
    assert next(r for r in rows if r["kind"] == "reverify")["review"] == "challenger-01.yaml"
    assert next(r for r in rows if r["kind"] == "worker")["activity_effort"] == "high"
    assert review_gaps(rows, CONTEXT) == []


def test_historical_or_other_workflow_workers_cannot_authorize_current_planning():
    history = [row("worker", segment=0), row("worker", workflow="sdd-spec-feature")]
    assert not reviewed({"reports": history, "report_context": CONTEXT})
    assert reviewed({"reports": [*history, row("worker", 2)], "report_context": CONTEXT})
    assert not reviewed({"reports": [row("worker"), row("worker", 2, status="needs_input")], "report_context": CONTEXT})
    # devkit's unscoped legacy records count in every segment.
    assert reviewed({"reports": [row("worker", workflow=None, segment=None)], "report_context": CONTEXT})


def test_required_support_role_gaps_are_scoped_to_the_current_planning_segment():
    rows = [row("worker", activity_effort="high"), row("challenger", segment=0), row("scout", workflow="other")]
    gaps = review_gaps(rows, CONTEXT)
    assert len(gaps) == 2 and any("challenger" in gap for gap in gaps) and any("scout" in gap for gap in gaps)
    assert review_gaps([*rows, row("challenger"), row("scout")], CONTEXT) == []
