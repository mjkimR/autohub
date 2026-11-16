from datetime import UTC, datetime
from uuid import uuid4

from app.features.project_management.pipeline_runs.outcome_schemas import DecisionOutcome
from app.features.project_management.work_plans.recovery_schemas import RecoveryEventRead, WorkItemRecoveryRead
from app.mcp.delivery_views import outcome_view, recovery_view


def test_outcome_omits_private_answer():
    row = DecisionOutcome(
        operation="answer",
        request_id=uuid4(),
        run_id=uuid4(),
        record_state="recorded",
        run_revision=1,
        run_state="blocked",
        observed_at=datetime.now(UTC),
        answer_text="PRIVATE",
    )
    view = outcome_view(row)
    assert "PRIVATE" not in view.model_dump_json()


def test_recovery_private_snapshots_and_event_maps_never_serialize():
    now = datetime.now(UTC)
    event = dict(id=uuid4(), kind="accepted", detail="accepted", evidence={"private": "PRIVATE"}, created_at=now)
    row = WorkItemRecoveryRead(
        id=uuid4(),
        request_id=uuid4(),
        actor="machine:test",
        reason="reviewed",
        command={"token": "PRIVATE"},
        prior_outcome={"description": "PRIVATE"},
        accepted_revision=1,
        accepted_run_revision=None,
        state="accepted",
        detail="accepted",
        created_at=now,
        events=[RecoveryEventRead.model_validate(event)] * 101,
    )
    view = recovery_view(row)
    assert "PRIVATE" not in view.model_dump_json()
    assert len(view.events) == 100 and view.event_count == 101 and view.events_omitted
