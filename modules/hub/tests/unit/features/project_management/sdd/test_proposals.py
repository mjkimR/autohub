import pytest
from app.features.project_management.sdd.proposals import proposal_state

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("status", ["draft", "reviewing", "accepted", "rejected", "unknown"])
def test_status_and_size_are_descriptive_not_activity_eligibility(status):
    text = f"---\nstatus: {status}\nsize: XL\nneeds_decompose: true\n---\n"
    row = proposal_state("demo", text, set(), {}, None)
    assert row["status"] == status
    assert row["actions"] == ["start_planning", "start_development"]
    assert "responsibility" in row["note"]


def test_active_run_is_an_owner_not_a_workflow_gate():
    row = proposal_state("demo", "---\nstatus: accepted\n---", set(), {}, {"id": "run"})
    assert row["actions"] == []
