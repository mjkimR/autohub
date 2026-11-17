"""The implementation-stage PR read retains Draft and head without workflow results of its own."""

from datetime import UTC, datetime

import pytest
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.usecases.implementation import record_implementation_observation

OBSERVED = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)
HEAD = "c" * 40


def pull(head: str = HEAD, *, draft: bool = True, state: str = "open") -> dict:
    return {"state": state, "draft": draft, "head": {"sha": head}}


def previous(verification: str, head: str = HEAD) -> dict:
    return {
        "head_sha": head,
        "draft": False,
        "verification": verification,
        "reason": "Required jobs failed: lint",
        "observed_at": "2026-11-17T08:00:00Z",
    }


def recorded(run: PipelineRun) -> dict:
    assert run.pull_observation is not None
    return run.pull_observation


def test_first_read_records_draft_and_an_unverified_head():
    run = PipelineRun(revision=3, pull_observation=None)

    record_implementation_observation(run, pull(), OBSERVED)

    assert run.pull_observation == {
        "head_sha": HEAD,
        "draft": True,
        "verification": "waiting",
        "reason": "Awaiting verification",
        "observed_at": "2026-11-17T09:00:00Z",
    }
    assert run.revision == 3


@pytest.mark.parametrize("verification", ["failed", "passed", "blocked", "waiting"])
def test_an_unchanged_head_keeps_its_last_verification(verification):
    run = PipelineRun(pull_observation=previous(verification))

    record_implementation_observation(run, pull(draft=True), OBSERVED)

    observed = recorded(run)
    assert (observed["draft"], observed["verification"]) == (True, verification)
    assert observed["reason"] == "Required jobs failed: lint"
    assert observed["observed_at"] == "2026-11-17T09:00:00Z"


def test_a_new_head_is_waiting_for_verification():
    run = PipelineRun(pull_observation=previous("passed"))

    record_implementation_observation(run, pull("f" * 40, draft=False), OBSERVED)

    observed = recorded(run)
    assert (observed["head_sha"], observed["draft"], observed["verification"]) == ("f" * 40, False, "waiting")
    assert observed["reason"] == "Awaiting verification"


def test_a_closed_pull_reads_closed():
    run = PipelineRun(pull_observation=previous("passed"))

    record_implementation_observation(run, pull(state="closed", draft=False), OBSERVED)

    assert (recorded(run)["verification"], recorded(run)["reason"]) == ("closed", "PR is closed")


def test_a_reopened_pull_does_not_keep_closed():
    run = PipelineRun(pull_observation=previous("closed"))

    record_implementation_observation(run, pull(), OBSERVED)

    assert recorded(run)["verification"] == "waiting"
