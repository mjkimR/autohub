"""Exact native artifacts are recovered without admitting a replacement operation."""

from unittest.mock import AsyncMock

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import activities

from tests.unit.features.project_management.sdd.test_activities import BASE, request, started

__all__ = ["started"]
pytestmark = pytest.mark.unit


async def test_owned_branch_recovers_after_unrelated_base_advance(started):
    github, branches, enrolled, project, starter = started
    github.refs.update({"main": "c" * 40, "plan-demo": "b" * 40})
    github.pulls = [
        {
            "number": 42,
            "head": {"ref": "plan-demo", "sha": "b" * 40},
            "base": {"ref": "main"},
            "body": activities.marker("plan", "demo"),
        }
    ]
    checkpoint = AsyncMock()
    await starter.start(
        project,
        "plan",
        "demo",
        request(),
        "user:operator",
        expected_base_sha=BASE,
        checkpoint=checkpoint,
        saved={"initial_sha": "b" * 40, "pull_number": 42},
    )
    assert not branches
    assert enrolled[0].pull_number == 42


async def test_base_move_during_policy_causes_zero_branch_effects(started, monkeypatch):
    github, branches, enrolled, project, starter = started

    async def changed(*args):
        github.refs["main"] = "c" * 40
        return None

    original_branch = activities.start_branch

    async def branch(*args, **kwargs):
        return await original_branch(*args)

    monkeypatch.setattr(activities, "start_branch", branch)
    monkeypatch.setattr(activities, "start_blocker", changed)
    with pytest.raises(ProjectError, match="Base moved"):
        await starter.start(
            project,
            "plan",
            "demo",
            request(),
            "user:operator",
            expected_base_sha=BASE,
            checkpoint=AsyncMock(),
            saved={},
        )
    assert not branches and not enrolled and not github.created


async def test_branch_only_recovery_reuses_candidate_and_creates_one_pr(started):
    github, branches, enrolled, project, starter = started
    github.refs["plan-demo"] = "b" * 40
    await starter.start(
        project,
        "plan",
        "demo",
        request(),
        "user:operator",
        expected_base_sha=BASE,
        checkpoint=AsyncMock(),
        saved={"initial_sha": "b" * 40},
    )
    assert not branches and len(github.created) == 1
    assert enrolled[0].pull_number == 42


async def test_base_move_during_local_candidate_prevents_remote_branch_publication(started, monkeypatch):
    github, branches, enrolled, project, starter = started

    async def candidate(*args, checkpoint, **kwargs):
        github.refs["main"] = "c" * 40
        await checkpoint(initial_sha="b" * 40, branch="plan-demo", base_sha=BASE)
        branches.append("published")
        return "b" * 40

    monkeypatch.setattr(activities, "start_branch", candidate)
    with pytest.raises(ProjectError, match="before native branch publication"):
        await starter.start(
            project,
            "plan",
            "demo",
            request(),
            "user:operator",
            expected_base_sha=BASE,
            checkpoint=AsyncMock(),
            saved={},
        )
    assert not branches and not enrolled


@pytest.mark.parametrize("artifact", ["missing_branch", "missing_pr", "closed_pr"])
async def test_recorded_artifact_absence_or_closure_never_creates_replacement(started, monkeypatch, artifact):
    github, branches, enrolled, project, starter = started
    saved: dict[str, str | int] = {"initial_sha": "b" * 40}
    if artifact != "missing_branch":
        github.refs["plan-demo"] = "b" * 40
        saved["pull_number"] = 42
    if artifact == "closed_pr":
        github.pulls = [
            {
                "number": 42,
                "state": "closed",
                "head": {"ref": "plan-demo", "sha": "b" * 40},
                "base": {"ref": "main"},
                "body": activities.marker("plan", "demo"),
            }
        ]

    async def branch(*args, checkpoint, **kwargs):
        await checkpoint(initial_sha="d" * 40, branch="plan-demo", base_sha=BASE)
        branches.append("replacement")
        return "d" * 40

    monkeypatch.setattr(activities, "start_branch", branch)
    with pytest.raises(ProjectError):
        await starter.start(
            project,
            "plan",
            "demo",
            request(),
            "user:operator",
            expected_base_sha=BASE,
            checkpoint=AsyncMock(),
            saved=saved,
        )
    assert not branches and not github.created and not enrolled


async def test_saved_pr_number_is_recovered_even_when_other_base_pr_sorts_first(started):
    github, branches, enrolled, project, starter = started
    github.refs["plan-demo"] = "b" * 40
    github.pulls = [
        {
            "number": number,
            "head": {"ref": "plan-demo", "sha": "b" * 40},
            "base": {"ref": base},
            "body": activities.marker("plan", "demo"),
        }
        for number, base in [(43, "other"), (42, "main")]
    ]
    await starter.start(
        project,
        "plan",
        "demo",
        request(),
        "user:operator",
        expected_base_sha=BASE,
        checkpoint=AsyncMock(),
        saved={"initial_sha": "b" * 40, "pull_number": 42},
    )
    assert not branches and not github.created and enrolled[0].pull_number == 42


async def test_lost_pr_result_that_is_now_closed_holds_exact_artifact(started):
    github, branches, enrolled, project, starter = started
    github.refs["plan-demo"] = "b" * 40
    github.pulls = [
        {
            "number": 42,
            "state": "closed",
            "head": {"ref": "plan-demo", "sha": "b" * 40},
            "base": {"ref": "main"},
            "body": activities.marker("plan", "demo"),
        }
    ]
    checkpoint = AsyncMock()
    with pytest.raises(ProjectError, match="closed"):
        await starter.start(
            project,
            "plan",
            "demo",
            request(),
            "user:operator",
            expected_base_sha=BASE,
            checkpoint=checkpoint,
            saved={"initial_sha": "b" * 40},
        )
    assert not branches and not github.created and not enrolled
    checkpoint.assert_awaited_once_with(pull_number=42)
