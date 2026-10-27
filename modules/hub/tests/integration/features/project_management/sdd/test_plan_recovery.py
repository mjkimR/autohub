"""Automatic publication recovery preserves authorization without dispatching another agent."""

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import plan_publication

from tests.integration.features.project_management.sdd import test_cli as cli
from tests.integration.features.project_management.sdd import test_native as scenarios
from tests.integration.features.project_management.sdd import test_plan_authorization as authorization

checkout = cli.checkout
project = scenarios.project
github = scenarios.github
proposal_run = scenarios.proposal_run
automatic = authorization.automatic
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_development_handoff_never_publishes_a_planning_decision(
    client, project, github, checkout, tmp_path, monkeypatch
):
    root, _ = checkout
    cli.reviewing_proposal(root, automatic=True)
    cli.run(
        root,
        cli.devkit_binary(),
        "workflow",
        "envelope",
        "worker",
        "--unit",
        cli.PROPOSAL,
        "--stage",
        "direction-handoff",
        "--summary",
        "Planning complete",
        "--effort",
        "low",
    )
    cli.run(root, cli.devkit_binary(), "spec", "proposal", "accept", "demo", "--by", "policy")
    head = cli.commit(root, "Accepted proposal before Development")
    bare = cli.bare_remote(root, tmp_path, head, monkeypatch)
    cli.run(bare, "git", "update-ref", "refs/heads/dev-demo", head)
    github.head_sha = head
    github.draft = True
    original = github.pull
    monkeypatch.setattr(
        github,
        "pull",
        lambda: {
            **original(),
            "head": {**original()["head"], "ref": "dev-demo"},
            "base": {**original()["base"], "sha": head},
        },
    )
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"expected_revision": project["revision"], "project_type": "sdd"},
    )
    assert changed.status_code == 200, changed.text
    created = await client.post(
        f"/api/v1/projects/{project['id']}/runs",
        json={"pull_number": 7, "spec_dir": cli.PROPOSAL, "handoff": True},
    )
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["sdd_snapshot"]["handoff_pending"]
    started = await scenarios.merge.advance(client, run)
    assert started["state"] == "implementing", started
    for _ in range(2):
        observed = await scenarios.merge.advance(client, run)
        assert observed["state"] == "implementing", observed
    path = f"/api/v1/pipeline-runs/{run['id']}"
    assert (await client.get(path + "/sdd-decisions")).json() == []
    assert len((await client.get(path + "/attempts")).json()["items"]) == 1
    assert cli.run(bare, "git", "rev-parse", "refs/heads/dev-demo") == head

    cli.run(root, "git", "checkout", "-q", "-b", "dev-demo")
    cli.run(root, cli.devkit_binary(), "spec", "proposal", "handoff", "demo")
    github.head_sha = cli.commit(root, "Handoff to Development")
    cli.run(root, "git", "push", "--quiet", str(bare), "HEAD:refs/heads/dev-demo")
    rebound = await scenarios.merge.advance(client, run)
    assert rebound["state"] == "implementing", rebound
    assert rebound["sdd_snapshot"]["spec_dir"].startswith("specs/")
    assert not rebound["sdd_snapshot"].get("handoff_pending")
    assert not rebound["sdd_progress"].get("plan_decision")


@pytest.mark.parametrize(
    "interruption", [None, "revoke", "question", "dismissed_question", "cancel", "disable", "base"]
)
async def test_automatic_lost_database_result_recovers_without_an_extra_attempt_or_publication(
    client, automatic, github, monkeypatch, interruption, project
):
    state, enroll = automatic
    state["complete"] = True
    run = await enroll()
    await scenarios.merge.advance(client, run)
    finish = plan_publication.PlanDecisionPublisher.finish

    async def fail_commit(*args, **kwargs):
        raise ProjectError(503, "Simulated database failure after successful Git push")

    monkeypatch.setattr(plan_publication.PlanDecisionPublisher, "finish", fail_commit)
    failed = await scenarios.merge.advance(client, run)
    assert failed["state"] == "blocked" and len(state["decisions"]) == 1, failed
    monkeypatch.setattr(plan_publication.PlanDecisionPublisher, "finish", finish)
    path = f"/api/v1/pipeline-runs/{run['id']}"
    before = (await client.get(path + "/attempts")).json()["items"]
    history = (await client.get(path + "/sdd-decisions")).json()
    assert history[0]["publication"]["state"] == "uncertain"
    assert history[0]["publication"]["recovery_revision"] == failed["revision"] != history[0]["revision"]
    if interruption == "revoke":
        revoked, _ = await scenarios.decide(client, failed, "revoke")
        assert revoked.status_code == 200, revoked.text
        failed = revoked.json()
    elif interruption in ("question", "dismissed_question"):
        _, question, failed = await authorization.ask(client, failed)
        if interruption == "dismissed_question":
            dismissed = await client.post(
                path + f"/questions/{question['id']}/dismiss",
                json={"expected_revision": failed["revision"], "reason": "Scope reviewed"},
            )
            assert dismissed.status_code == 200, dismissed.text
            failed = (await client.get(path)).json()
    elif interruption == "cancel":
        canceled = await client.post(path + "/cancel")
        assert canceled.status_code == 200, canceled.text
        failed = canceled.json()
    elif interruption == "disable":
        project_path = f"/api/v1/projects/{project['id']}"
        current = (await client.get(project_path)).json()
        disabled = await client.patch(project_path, json={"expected_revision": current["revision"], "enabled": False})
        assert disabled.status_code == 200, disabled.text
    elif interruption == "base":
        original = github.pull
        monkeypatch.setattr(github, "pull", lambda: {**original(), "base": {**original()["base"], "sha": "f" * 40}})
    resumed, body = await scenarios.decide(client, failed)
    if interruption in ("question", "cancel", "disable"):
        assert resumed.status_code == 409, resumed.text
        assert not (await client.get(path)).json()["sdd_progress"].get("approval")
        assert (await client.get(path + "/sdd-decisions")).json()[0]["publication"]["state"] == "uncertain"
    else:
        assert resumed.status_code == 200, resumed.text
        assert resumed.json()["state"] == ("blocked" if interruption else "awaiting_ci"), resumed.text
        assert bool(resumed.json()["sdd_progress"].get("approval")) is (interruption is None)
        history = (await client.get(path + "/sdd-decisions")).json()
        saved = next(row for row in history if row.get("automatic"))
        assert saved["publication"]["state"] == "published"
        assert saved["publication"]["applied"] is (interruption is None)
        replay = await client.post(path + "/resume", json=body)
        assert replay.status_code == 200 and replay.json()["revision"] == resumed.json()["revision"]
    after = (await client.get(path + "/attempts")).json()["items"]
    assert [attempt["id"] for attempt in after] == [attempt["id"] for attempt in before]
    if interruption == "cancel":
        assert after[0]["state"] == "failed"
    assert len(state["decisions"]) == 1 and github.merge_requests == 0
    if interruption is None:
        done = await scenarios.merge.advance(client, run)
        assert done["state"] == "completed" and github.merge_requests == 1, done
        assert len(state["decisions"]) == 1
