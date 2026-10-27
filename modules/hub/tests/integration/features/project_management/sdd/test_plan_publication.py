"""Proposal publication commits its intent before Git, fences stops and recovers uncertain outcomes."""

import asyncio

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import plan_publication

from tests.integration.features.project_management.sdd import test_native as scenarios

github = scenarios.github
project = scenarios.project
proposal_run = scenarios.proposal_run
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def history(client, run):
    return (await client.get(f"/api/v1/pipeline-runs/{run['id']}/sdd-decisions")).json()


async def test_withdrawn_proposal_approval_is_not_restored_by_inspection(client, proposal_run, github):
    _, enroll = proposal_run
    run = await enroll()
    waiting = await scenarios.merge.advance(client, run)
    accepted, _ = await scenarios.decide(client, waiting, "accept_plan", head_sha=scenarios.merge.HEAD)
    revoked, _ = await scenarios.decide(client, accepted.json(), "revoke")
    assert revoked.status_code == 200, revoked.text
    resumed, _ = await scenarios.decide(client, revoked.json())
    assert resumed.status_code == 200, resumed.text
    held = await scenarios.merge.advance(client, run)
    assert held["state"] == "blocked" and not held["sdd_progress"].get("approval")
    assert github.merge_requests == 0
    approved, _ = await scenarios.decide(client, held, "approve")
    assert approved.status_code == 200, approved.text
    done = await scenarios.merge.advance(client, run)
    assert done["state"] == "completed" and github.merge_requests == 1


@pytest.mark.parametrize("stop", ["cancel", "disable"])
async def test_stop_before_publication_prevents_external_write(client, project, proposal_run, monkeypatch, stop):
    state, enroll = proposal_run
    run = await enroll()
    waiting = await scenarios.merge.advance(client, run)
    record = plan_publication.record_plan_decision

    monkeypatch.setattr(scenarios, "COMMIT", "e" * 40)

    async def stop_then_publish(*args, **kwargs):
        if stop == "cancel":
            response = await client.post(f"/api/v1/pipeline-runs/{run['id']}/cancel")
        else:
            path = f"/api/v1/projects/{project['id']}"
            latest = (await client.get(path)).json()
            response = await client.patch(path, json={"expected_revision": latest["revision"], "enabled": False})
        assert response.status_code == 200, response.text
        return await record(*args, **kwargs)

    monkeypatch.setattr(plan_publication, "record_plan_decision", stop_then_publish)
    response, _ = await scenarios.decide(client, waiting, "accept_plan", head_sha=scenarios.merge.HEAD)
    assert response.status_code == 409, response.text
    assert not state["decisions"] and state["status"] == "reviewing"
    rows = await history(client, run)
    assert rows[0]["publication"]["state"] == "uncertain"
    assert not rows[0].get("plan_decision")  # intent is not an approval


@pytest.mark.parametrize("cancel_after_push", [False, True])
async def test_lost_database_result_recovers_exact_pushed_commit_without_publishing_again(
    client, proposal_run, github, monkeypatch, cancel_after_push
):
    state, enroll = proposal_run
    run = await enroll()
    waiting = await scenarios.merge.advance(client, run)
    # A real decision commit differs from its parent; expose it only after the external effect.
    candidate = "e" * 40
    monkeypatch.setattr(scenarios, "COMMIT", candidate)
    original_pull = github.pull
    monkeypatch.setattr(
        github,
        "pull",
        lambda: {
            **original_pull(),
            "head": {**original_pull()["head"], "sha": candidate if state["decisions"] else scenarios.merge.HEAD},
        },
    )
    finish = plan_publication.PlanDecisionPublisher.finish

    async def fail_commit(*args, **kwargs):
        raise ProjectError(503, "Simulated database failure after successful Git push")

    monkeypatch.setattr(plan_publication.PlanDecisionPublisher, "finish", fail_commit)
    failed, body = await scenarios.decide(client, waiting, "accept_plan", head_sha=scenarios.merge.HEAD)
    assert failed.status_code == 503 and len(state["decisions"]) == 1
    pending = (await history(client, run))[0]
    assert pending["publication"]["state"] == "uncertain"
    assert pending["publication"]["candidates"][0]["commit_sha"] == candidate
    if cancel_after_push:
        assert (await client.post(f"/api/v1/pipeline-runs/{run['id']}/cancel")).status_code == 200
    monkeypatch.setattr(plan_publication.PlanDecisionPublisher, "finish", finish)
    recovered = await client.post(f"/api/v1/pipeline-runs/{run['id']}/resume", json=body)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["state"] == ("canceled" if cancel_after_push else "awaiting_ci")
    assert len(state["decisions"]) == 1
    saved = (await history(client, run))[0]
    assert saved["publication"]["state"] == "published"
    assert saved["publication"]["applied"] is not cancel_after_push
    assert bool(recovered.json()["sdd_progress"].get("approval")) is not cancel_after_push


async def test_failed_push_retries_the_same_request_without_losing_audit(client, proposal_run, monkeypatch):
    state, enroll = proposal_run
    run = await enroll()
    waiting = await scenarios.merge.advance(client, run)
    record = plan_publication.record_plan_decision
    monkeypatch.setattr(scenarios, "COMMIT", "e" * 40)

    async def fail_push(*args, **kwargs):
        original_guard = kwargs["publication"]
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def guard(plan):
            async with original_guard(plan):
                raise ProjectError(422, "Git push failed before writing")
                yield

        return await record(*args, **{**kwargs, "publication": guard})

    monkeypatch.setattr(plan_publication, "record_plan_decision", fail_push)
    failed, body = await scenarios.decide(client, waiting, "accept_plan", head_sha=scenarios.merge.HEAD)
    assert failed.status_code == 422 and not state["decisions"]
    monkeypatch.setattr(plan_publication, "record_plan_decision", record)
    retried = await client.post(f"/api/v1/pipeline-runs/{run['id']}/resume", json=body)
    assert retried.status_code == 200 and len(state["decisions"]) == 1
    assert len(await history(client, run)) == 1


async def test_cancellation_waits_for_a_publication_that_already_holds_the_fence(
    client, proposal_run, monkeypatch, is_postgres
):
    if not is_postgres:
        pytest.skip("Publication/cancel lock contention requires PostgreSQL")
    state, enroll = proposal_run
    run = await enroll()
    waiting = await scenarios.merge.advance(client, run)
    record = plan_publication.record_plan_decision
    entered, release = asyncio.Event(), asyncio.Event()

    async def delayed(*args, **kwargs):
        from contextlib import asynccontextmanager

        original_guard = kwargs["publication"]

        @asynccontextmanager
        async def guard(plan):
            async with original_guard(plan):
                entered.set()
                await release.wait()
                yield

        return await record(*args, **{**kwargs, "publication": guard})

    monkeypatch.setattr(plan_publication, "record_plan_decision", delayed)
    decision = asyncio.create_task(scenarios.decide(client, waiting, "accept_plan", head_sha=scenarios.merge.HEAD))
    await asyncio.wait_for(entered.wait(), 5)
    cancel = asyncio.create_task(client.post(f"/api/v1/pipeline-runs/{run['id']}/cancel"))
    try:
        await asyncio.sleep(0.1)
        assert not cancel.done()
    finally:
        release.set()
    response, _ = await decision
    canceled = await cancel
    assert response.status_code == canceled.status_code == 200
    assert canceled.json()["state"] == "canceled" and len(state["decisions"]) == 1
    assert (await history(client, run))[0]["publication"]["state"] == "published"


@pytest.mark.parametrize("base_auto", [True, False])
@pytest.mark.parametrize("accepted_by_agent", [True, False])
async def test_auto_plan_acceptance_requires_owning_base_and_records_policy_authority(
    client, proposal_run, github, monkeypatch, base_auto, accepted_by_agent
):
    state, enroll = proposal_run
    inspect = scenarios.native.SddService.inspect

    async def automatic(*args, **kwargs):
        value = await inspect(*args, **kwargs)
        value["current"].update(complete=True, stage=None, requests=[])
        value["snapshot"]["policy"]["approvals"]["plan-accept"] = {"policy": "auto"}
        value["base_policy"] = {"approvals": {"plan-accept": {"policy": "auto" if base_auto else "ask"}}}
        return value

    monkeypatch.setattr(scenarios.native.SddService, "inspect", automatic)
    if accepted_by_agent:
        state["status"] = "accepted"
    github.draft = True
    run = await enroll()
    advanced = await scenarios.merge.advance(client, run)
    if advanced["state"] == "implementing":
        advanced = await scenarios.merge.advance(client, run)
    assert advanced["state"] == ("awaiting_ci" if base_auto else "blocked"), advanced
    if base_auto:
        assert len(state["decisions"]) == 1 and state["decisions"][0]["authority"] == "policy"
        assert advanced["sdd_progress"]["approval"]["source"] == "plan-decision"
        github.draft = False
        done = await scenarios.merge.advance(client, run)
        assert done["state"] == "completed" and github.merge_requests == 1
    else:
        assert not state["decisions"] and not advanced["sdd_progress"].get("approval")
