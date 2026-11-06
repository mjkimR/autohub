from datetime import UTC, datetime
from uuid import uuid4

from app.features.project_management.pipeline_runs.outcome_schemas import DecisionOutcome
from app.features.project_management.work_plans.recovery_schemas import RecoveryEventRead, WorkItemRecoveryRead
from app.mcp.delivery_views import batch_view, outcome_view, recovery_view


def test_outcome_allowlist_and_bounded_candidates():
    row = DecisionOutcome(
        operation="answer",
        request_id=uuid4(),
        run_id=uuid4(),
        record_state="recorded",
        run_revision=1,
        run_state="blocked",
        observed_at=datetime.now(UTC),
        answer_text="PRIVATE",
        current_authority={"secret": "PRIVATE"},
        current_hold={"payload": "PRIVATE"},
        candidate_heads=[str(i) for i in range(51)],
    )
    view = outcome_view(row)
    assert "PRIVATE" not in view.model_dump_json()
    assert view.current_authority_present and view.current_hold_present
    assert len(view.candidate_heads) == 50 and view.candidate_head_count == 51 and view.candidate_heads_omitted


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


def test_batch_private_maps_and_latest_claim_history_disclosure():
    claim = dict(id=str(uuid4()), activity="dev", settled=True, uncertain=False, checkpoint={"payload": "PRIVATE"})
    latest = claim | {"id": str(uuid4()), "run_id": str(uuid4())}
    member = dict(
        id=str(uuid4()),
        anchor_id="PROP-a",
        path="docs/proposals/PROP-a",
        position=0,
        phase="dev",
        state="running",
        initial={"private": "PRIVATE"},
        claims=[claim, latest],
    )
    row = dict(
        id=str(uuid4()),
        project_id=str(uuid4()),
        state="running",
        revision=1,
        exclusion=True,
        detail=None,
        basis={"token": "PRIVATE"},
        evaluation={"payload": "PRIVATE"},
        members=[member] * 51,
    )
    view = batch_view(row)
    assert "PRIVATE" not in view.model_dump_json()
    assert len(view.members) == 50 and view.members_omitted and view.member_count == 51
    assert view.members[0].latest_claim is not None
    assert (
        str(view.members[0].latest_claim.id) == latest["id"]
        and view.members[0].claim_count == 2
        and view.members[0].history_omitted
    )
