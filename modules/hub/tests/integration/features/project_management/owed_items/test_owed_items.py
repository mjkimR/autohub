from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from app.features.ai_catalogs.models import AICatalog, AICatalogState
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.sdd.batch_models import SddActivityClaim, SddBatch, SddBatchMember
from app.features.project_management.work_plans.models import ItemDependency, WorkItem, WorkItemRecovery, WorkPlan
from app.features.project_management.work_plans.replacement_models import ReplacementAcceptance, ReplacementLink
from app_layer_base.utils.time_util import get_current_utc_time
from app_prebuilt_auth.user.deps import get_current_user
from sqlalchemy import event
from sqlalchemy.engine import Engine

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios
from tests.integration.features.project_management.pipeline_runs.test_interactions import ask, state

project = scenarios.project
github = scenarios.github
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
URL = "/api/v1/owed-items"
COUNTS = URL + "/counts"
DECISIONS = "/api/v1/pipeline-runs/decisions"
ALL_KINDS = {
    "decision",
    "stopped-run",
    "work-plan-proposed",
    "work-item-recovery",
    "work-item-replacement",
    "work-item-attention",
    "sdd-batch-attention",
    "connection-test-cleanup",
    "failed-run",
}


@pytest.fixture
def owed(project):
    return project


async def enroll(client, github, project, number):
    github.pulls.setdefault(number, scenarios.pull(number))
    response = await scenarios.enroll(client, project, number)
    assert response.status_code == 201, response.text
    return response.json()


async def set_run(session, run_id, **values):
    run = await session.get(PipelineRun, UUID(run_id), populate_existing=True)
    for name, value in values.items():
        setattr(run, name, value)
    run.revision += 1
    await session.commit()
    return run


async def plan(session, project, state="active", title="Plan"):
    row = WorkPlan(
        project_id=UUID(project["id"]),
        title=title,
        description="Owed test plan",
        repository="owner/app",
        connector_id=UUID(project["github_connector_id"]),
        base_branch="main",
        state=state,
    )
    session.add(row)
    await session.flush()
    return row


async def item(session, plan_row, key, state="waiting", run_id=None):
    row = WorkItem(
        plan_id=plan_row.id,
        key=key,
        title=f"Item {key}",
        description="Do the work",
        acceptance="It works",
        state=state,
        pipeline_run_id=UUID(run_id) if run_id else None,
    )
    session.add(row)
    await session.flush()
    return row


async def recovery(session, project, plan_row, item_row, state):
    row = WorkItemRecovery(
        project_id=UUID(project["id"]),
        plan_id=plan_row.id,
        item_id=item_row.id,
        request_id=uuid4(),
        request_digest="a" * 64,
        actor="operator",
        reason="Retry unchanged work",
        command={},
        prior_outcome={"run": None},
        accepted_revision=1,
        state=state,
        detail="Checking original execution",
    )
    session.add(row)
    await session.flush()
    return row


async def batch(session, project, state="attention", run_id=None, exclusion=False, unit="specs/a"):
    row = SddBatch(
        project_id=UUID(project["id"]),
        request_id=uuid4(),
        request_digest="b" * 64,
        actor="operator",
        state=state,
        exclusion=exclusion,
        basis={},
        detail="Member needs the operator",
    )
    session.add(row)
    await session.flush()
    if run_id:
        member = SddBatchMember(batch_id=row.id, position=1, anchor_id=unit, path=unit, initial={}, phase="develop")
        session.add(member)
        await session.flush()
        session.add(
            SddActivityClaim(
                project_id=row.project_id,
                member_id=member.id,
                request_id=uuid4(),
                actor="operator",
                request_digest="c" * 64,
                unit=unit,
                activity="dev",
                checkpoint={},
                run_id=UUID(run_id),
            )
        )
        await session.flush()
    return row


async def connection_test(session, project, cleanup_status="pending", repository="owner/app"):
    now = get_current_utc_time()
    row = ConnectionTest(
        project_id=UUID(project["id"]),
        project_revision=1,
        repository=repository,
        connector_id=UUID(project["github_connector_id"]),
        catalog_snapshot={"kind": "jules", "adapter": "jules-api"},
        verification={},
        status="failed",
        phase="cleanup",
        cleanup_status=cleanup_status,
        evidence={"unconfirmed_pulls": {"5": {"head": "c" * 40}}},
        deadline=now,
        finished_at=now,
    )
    session.add(row)
    await session.flush()
    return row


async def activity_question(session, run_id):
    from app.features.project_management.pipeline_runs.models import RunQuestion

    row = await set_run(
        session,
        run_id,
        state="blocked",
        sdd_snapshot={"provider": "repository-agent", "execution_version": 2, "spec_dir": "docs/proposals/PROP-test"},
        sdd_progress=None,
    )
    session.add(
        RunQuestion(
            pipeline_run_id=row.id, head_sha="c" * 40, question="Pick", actor="test", source="agent", state="open"
        )
    )
    await session.commit()


async def items(client, **params):
    response = await client.get(URL, params={"limit": 100, **params})
    assert response.status_code == 200, response.text
    return response.json()["items"]


def by_kind(rows, kind):
    return [row for row in rows if row["kind"] == kind]


async def every_kind(client, github, session, project, offset=0):
    """One owed object of each kind; returns the subject IDs by kind."""
    n = 20 + offset * 20
    decided = await enroll(client, github, project, n)
    assert (await ask(client, f"/api/v1/pipeline-runs/{decided['id']}")).status_code == 200
    paused = await enroll(client, github, project, n + 1)
    assert (
        await client.post(f"/api/v1/pipeline-runs/{paused['id']}/pause", json={"reason": "Hold"})
    ).status_code == 200
    failed = await enroll(client, github, project, n + 2)
    await set_run(session, failed["id"], state="failed", pause_reason="CI failed")
    recovered = await enroll(client, github, project, n + 3)
    await set_run(session, recovered["id"], state="failed")
    attention_run = await enroll(client, github, project, n + 4)
    await set_run(session, attention_run["id"], state="paused")
    batch_run = await enroll(client, github, project, n + 5)
    await set_run(session, batch_run["id"], state="paused")

    proposed = await plan(session, project, state="proposed", title=f"Proposed {offset}")
    work = await plan(session, project, title=f"Work {offset}")
    failed_item = await item(session, work, "failed", state="failed", run_id=failed["id"])
    recovered_item = await item(session, work, "recovered", state="failed", run_id=recovered["id"])
    rec = await recovery(session, project, work, recovered_item, "accepted")
    attention_item = await item(session, work, "attention", state="attention", run_id=attention_run["id"])
    original = await item(session, work, "original", state="failed")
    dependent = await item(session, work, "dependent")
    replacement_plan = await plan(session, project, title=f"Replacement {offset}")
    replacement = await item(session, replacement_plan, "replacement", state="succeeded")
    session.add(ItemDependency(plan_id=work.id, item_id=dependent.id, depends_on_id=original.id))
    link = ReplacementLink(
        project_id=UUID(project["id"]),
        original_plan_id=work.id,
        original_item_id=original.id,
        replacement_plan_id=replacement_plan.id,
        replacement_item_id=replacement.id,
        snapshot={},
        actor="operator",
        reason="Replaced by a new plan",
    )
    session.add(link)
    held_batch = await batch(session, project, run_id=batch_run["id"], unit=f"specs/{offset}")
    cleanup = await connection_test(session, project)
    await session.commit()
    return {
        "decision_run": decided["id"],
        "paused": paused["id"],
        "failed": failed["id"],
        "failed_item": str(failed_item.id),
        "recovered_run": recovered["id"],
        "recovery": str(rec.id),
        "attention_item": str(attention_item.id),
        "attention_run": attention_run["id"],
        "proposed": str(proposed.id),
        "link": str(link.id),
        "link_original": original.id,
        "link_dependent": dependent.id,
        "link_plan": work.id,
        "batch": str(held_batch.id),
        "batch_run": batch_run["id"],
        "cleanup": str(cleanup.id),
    }


async def test_every_kind_has_one_item_with_stable_shape(client, owed, github, session):
    ids = await every_kind(client, github, session, owed)
    github.paths.clear()
    rows = await items(client)
    assert {row["kind"] for row in rows} == ALL_KINDS
    assert len(rows) == len(ALL_KINDS)
    for row in rows:
        assert set(row) == {
            "key",
            "kind",
            "counted",
            "cause",
            "subject",
            "primary_action",
            "waiting_since",
            "context",
        }
        assert row["key"] == f"{row['kind']}:{row['subject']['id']}"
        assert row["subject"]["project_id"] == owed["id"]
        assert set(row["context"]) == {"run_id", "work_plan_id", "work_item_id", "sdd_batch_id", "catalog_hold"}
        assert row["counted"] is (row["kind"] != "failed-run")
        assert row["cause"]
    decision = by_kind(rows, "decision")[0]
    entry = (await client.get(DECISIONS)).json()["items"][0]
    assert decision["key"] == "decision:" + entry["key"]
    assert decision["primary_action"]["name"] == "answer"
    assert decision["context"]["run_id"] == ids["decision_run"]
    stopped = by_kind(rows, "stopped-run")[0]
    assert stopped["subject"] == {
        "type": "pipeline-run",
        "id": ids["paused"],
        "project_id": owed["id"],
        **{"title": stopped["subject"]["title"]},
    }
    assert stopped["primary_action"]["name"] == "resume-run"
    assert by_kind(rows, "work-plan-proposed")[0]["subject"]["id"] == ids["proposed"]
    assert by_kind(rows, "work-item-recovery")[0]["context"]["run_id"] == ids["recovered_run"]
    assert by_kind(rows, "work-item-replacement")[0]["subject"]["id"] == ids["link"]
    assert by_kind(rows, "work-item-replacement")[0]["primary_action"]["name"] == "accept-replacement"
    attention = by_kind(rows, "work-item-attention")[0]
    assert (
        attention["subject"]["id"] == ids["attention_item"] and attention["context"]["run_id"] == ids["attention_run"]
    )
    assert by_kind(rows, "sdd-batch-attention")[0]["subject"]["id"] == ids["batch"]
    cleanup = by_kind(rows, "connection-test-cleanup")[0]
    assert cleanup["subject"]["id"] == ids["cleanup"] and cleanup["primary_action"]["name"] == "review-cleanup"
    failed = by_kind(rows, "failed-run")[0]
    assert failed["subject"]["id"] == ids["failed"] and failed["context"]["work_item_id"] == ids["failed_item"]
    assert failed["counted"] is False
    # Suppressed owners never appear on their own.
    run_subjects = {row["subject"]["id"] for row in rows if row["subject"]["type"] == "pipeline-run"}
    assert run_subjects == {ids["paused"], ids["failed"]}
    assert not github.paths

    counts = (await client.get(COUNTS)).json()
    assert set(counts["by_kind"]) == ALL_KINDS
    assert counts["by_kind"]["failed-run"] == 1
    assert counts["total"] == len(ALL_KINDS) - 1
    assert counts["total"] == sum(v for k, v in counts["by_kind"].items() if k != "failed-run")
    assert counts["by_project"] == {owed["id"]: counts["total"]}
    assert not github.paths

    # A cause change within the same kind and subject keeps the key.
    await set_run(session, ids["paused"], state="blocked", pause_reason="Blocked for review")
    blocked = by_kind(await items(client, kind="stopped-run"), "stopped-run")[0]
    assert blocked["key"] == stopped["key"] and blocked["cause"] != stopped["cause"]


async def test_decisions_suppress_runs_and_match_the_inbox_count(client, owed, github, session):
    asked = await enroll(client, github, owed, 7)
    root = f"/api/v1/pipeline-runs/{asked['id']}"
    question = (await ask(client, root)).json()
    native = await enroll(client, github, owed, 8)
    await activity_question(session, native["id"])
    other = await client.post(
        "/api/v1/projects",
        json={
            "name": "Other",
            "repository": "owner/other",
            "github_connector_id": owed["github_connector_id"],
            "verification": scenarios.VERIFICATION,
        },
    )
    assert other.status_code == 201
    rows = await items(client)
    assert [row["kind"] for row in rows] == ["decision", "decision"]
    assert {row["context"]["run_id"] for row in rows} == {asked["id"], native["id"]}
    for params in ({}, {"project_id": owed["id"]}, {"project_id": other.json()["id"]}):
        inbox = (await client.get(DECISIONS, params=params)).json()["actionable_total_count"]
        counts = (await client.get(COUNTS, params=params)).json()
        assert counts["by_kind"]["decision"] == inbox, params
    dismissed = await client.post(
        root + f"/questions/{question['id']}/dismiss",
        json={"expected_revision": (await state(client, root))["revision"], "reason": "Not needed"},
    )
    assert dismissed.status_code == 200
    rows = await items(client)
    assert sorted(row["kind"] for row in rows) == ["decision", "stopped-run"]
    stopped = by_kind(rows, "stopped-run")[0]
    assert stopped["subject"]["id"] == asked["id"] and stopped["cause"].startswith("Run is blocked")
    assert (await client.get(COUNTS)).json()["by_kind"]["decision"] == (await client.get(DECISIONS)).json()[
        "actionable_total_count"
    ]


async def test_stopped_runs_carry_only_their_own_catalog_hold(client, owed, github, session):
    manual = await enroll(client, github, owed, 7)
    assert (await client.post(f"/api/v1/pipeline-runs/{manual['id']}/pause", json={})).status_code == 200
    blocked = await enroll(client, github, owed, 8)
    await set_run(session, blocked["id"], state="blocked", pause_reason="Merge gating")
    held = await enroll(client, github, owed, 9)
    catalog = AICatalog(
        key="held",
        name="held",
        kind="codex",
        adapter="codex-github-mention",
        availability_state=AICatalogState.QUOTA_BLOCKED,
        available_at=get_current_utc_time() + timedelta(hours=2),
        revision=1,
    )
    session.add(catalog)
    await session.flush()
    await set_run(session, held["id"], state="paused", ai_catalog_id=catalog.id)
    rows = await items(client)
    assert sorted(row["subject"]["id"] for row in rows) == sorted([manual["id"], blocked["id"], held["id"]])
    assert {row["kind"] for row in rows} == {"stopped-run"}
    assert all(row["counted"] and row["primary_action"]["name"] == "resume-run" for row in rows)
    holds = {row["subject"]["id"]: row["context"]["catalog_hold"] for row in rows}
    assert holds[manual["id"]] is None and holds[blocked["id"]] is None
    assert holds[held["id"]]["catalog_id"] == str(catalog.id)
    assert holds[held["id"]]["reason"] == "quota-blocked"


async def test_failed_runs_are_quiet_and_recovery_wins(client, owed, github, session):
    quiet = await enroll(client, github, owed, 7)
    await set_run(session, quiet["id"], state="failed")
    recovering = await enroll(client, github, owed, 8)
    await set_run(session, recovering["id"], state="failed")
    admitted = await enroll(client, github, owed, 9)
    await set_run(session, admitted["id"], state="failed")
    work = await plan(session, owed)
    quiet_item = await item(session, work, "quiet", state="failed", run_id=quiet["id"])
    rec_item = await item(session, work, "rec", state="failed", run_id=recovering["id"])
    adm_item = await item(session, work, "adm", state="failed", run_id=admitted["id"])
    rec = await recovery(session, owed, work, rec_item, "accepted")
    await recovery(session, owed, work, adm_item, "awaiting-admission")
    await session.commit()
    rows = await items(client)
    failed = by_kind(rows, "failed-run")
    assert {row["subject"]["id"] for row in failed} == {quiet["id"], admitted["id"]}
    assert {row["context"]["work_item_id"] for row in failed} == {str(quiet_item.id), str(adm_item.id)}
    assert all(row["counted"] is False for row in failed)
    recovery_rows = by_kind(rows, "work-item-recovery")
    assert [row["subject"]["id"] for row in recovery_rows] == [str(rec.id)]
    assert recovery_rows[0]["context"]["run_id"] == recovering["id"]
    counts = (await client.get(COUNTS)).json()
    assert counts["total"] == 1 and counts["by_kind"]["failed-run"] == 2
    rec.state = "reconciling"
    await session.commit()
    assert len(by_kind(await items(client), "work-item-recovery")) == 1
    rec.state = "running"
    await session.commit()
    rows = await items(client)
    assert not by_kind(rows, "work-item-recovery")
    assert recovering["id"] in {row["subject"]["id"] for row in by_kind(rows, "failed-run")}


async def test_work_plan_and_work_item_kinds(client, owed, github, session):
    paused = await enroll(client, github, owed, 7)
    await set_run(session, paused["id"], state="paused")
    proposed = await plan(session, owed, state="proposed")
    work = await plan(session, owed)
    attention = await item(session, work, "attention", state="attention", run_id=paused["id"])
    await session.commit()
    rows = await items(client)
    assert sorted(row["kind"] for row in rows) == ["work-item-attention", "work-plan-proposed"]
    assert by_kind(rows, "work-plan-proposed")[0]["subject"]["id"] == str(proposed.id)
    attention_row = by_kind(rows, "work-item-attention")[0]
    assert attention_row["subject"]["id"] == str(attention.id)
    assert attention_row["context"] == {
        "run_id": paused["id"],
        "work_plan_id": str(work.id),
        "work_item_id": str(attention.id),
        "sdd_batch_id": None,
        "catalog_hold": None,
    }
    proposed.state = "draft"
    attention.state = "running"
    await session.commit()
    rows = await items(client)
    assert [row["kind"] for row in rows] == ["stopped-run"]


async def test_replacement_waits_until_the_edge_is_accepted(client, owed, github, session):
    work = await plan(session, owed)
    original = await item(session, work, "original", state="failed")
    dependent = await item(session, work, "dependent")
    replacement_plan = await plan(session, owed, title="Replacement")
    replacement = await item(session, replacement_plan, "replacement", state="succeeded")
    session.add(ItemDependency(plan_id=work.id, item_id=dependent.id, depends_on_id=original.id))
    link = ReplacementLink(
        project_id=UUID(owed["id"]),
        original_plan_id=work.id,
        original_item_id=original.id,
        replacement_plan_id=replacement_plan.id,
        replacement_item_id=replacement.id,
        snapshot={},
        actor="operator",
        reason="Replaced",
    )
    session.add(link)
    await session.commit()
    rows = await items(client)
    assert [(row["kind"], row["subject"]["id"]) for row in rows] == [("work-item-replacement", str(link.id))]
    assert rows[0]["primary_action"]["name"] == "accept-replacement"
    assert rows[0]["context"]["work_item_id"] == str(original.id)
    session.add(
        ReplacementAcceptance(
            link_id=link.id,
            plan_id=work.id,
            dependent_item_id=dependent.id,
            original_item_id=original.id,
            snapshot={},
            actor="operator",
            reason="Equivalent",
        )
    )
    await session.commit()
    assert await items(client) == []


async def test_batch_attention_suppresses_its_run_and_yields_to_decisions(client, owed, github, session):
    # Enroll before uncommitted owner rows exist: PostgreSQL enrollment locks the project row.
    paused = await enroll(client, github, owed, 7)
    await set_run(session, paused["id"], state="paused")
    decided = await enroll(client, github, owed, 8)
    await activity_question(session, decided["id"])
    first = await batch(session, owed, run_id=paused["id"], unit="specs/one")
    second = await batch(session, owed, run_id=decided["id"], unit="specs/two")
    await session.commit()
    rows = await items(client)
    assert sorted(row["kind"] for row in rows) == ["decision", "sdd-batch-attention"]
    assert by_kind(rows, "sdd-batch-attention")[0]["subject"]["id"] == str(first.id)
    decision = by_kind(rows, "decision")[0]
    assert decision["context"]["run_id"] == decided["id"]
    assert decision["context"]["sdd_batch_id"] == str(second.id)


async def test_a_batch_yielding_to_a_decision_hides_no_other_stopped_run(client, owed, github, session):
    decided = await enroll(client, github, owed, 7)
    await activity_question(session, decided["id"])
    paused = await enroll(client, github, owed, 8)
    await set_run(session, paused["id"], state="paused")
    shared = await batch(session, owed, run_id=decided["id"], unit="specs/one")
    member = SddBatchMember(
        batch_id=shared.id, position=2, anchor_id="specs/two", path="specs/two", initial={}, phase="develop"
    )
    session.add(member)
    await session.flush()
    session.add(
        SddActivityClaim(
            project_id=shared.project_id,
            member_id=member.id,
            request_id=uuid4(),
            actor="operator",
            request_digest="c" * 64,
            unit="specs/two",
            activity="dev",
            checkpoint={},
            run_id=UUID(paused["id"]),
        )
    )
    await session.commit()
    rows = await items(client)
    # The batch yields to the decision, so the other paused run stays listed on its own.
    assert sorted(row["kind"] for row in rows) == ["decision", "stopped-run"]
    assert by_kind(rows, "stopped-run")[0]["subject"]["id"] == paused["id"]


async def test_connection_cleanup_review_until_completed(client, owed, github, session):
    open_review = await connection_test(session, owed)
    done = await connection_test(session, owed, cleanup_status="completed", repository="owner/done")
    other_adapter = await connection_test(session, owed, repository="owner/codex")
    other_adapter.catalog_snapshot = {"kind": "codex", "adapter": "codex-github-mention"}
    pending_scan = await connection_test(session, owed, repository="owner/scan")
    pending_scan.evidence = {"output_discovery_pending": True}
    no_evidence = await connection_test(session, owed, repository="owner/none")
    no_evidence.evidence = {"unconfirmed_pulls": {}}
    running = await connection_test(session, owed, repository="owner/running")
    running.status = "running"
    await session.commit()
    rows = await items(client)
    assert {row["subject"]["id"] for row in rows} == {str(open_review.id), str(pending_scan.id)}
    assert all(row["kind"] == "connection-test-cleanup" for row in rows)
    assert str(done.id) not in {row["subject"]["id"] for row in rows}
    open_review.cleanup_status = "completed"
    await session.commit()
    assert {row["subject"]["id"] for row in await items(client)} == {str(pending_scan.id)}


async def test_counts_are_filtered_by_project(client, owed, github, session):
    await every_kind(client, github, session, owed)
    other = await client.post(
        "/api/v1/projects",
        json={
            "name": "Other",
            "repository": "owner/other",
            "github_connector_id": owed["github_connector_id"],
            "verification": scenarios.VERIFICATION,
        },
    )
    other_project = other.json()
    await plan(session, other_project, state="proposed")
    await session.commit()
    everything = (await client.get(COUNTS)).json()
    assert everything["by_project"] == {owed["id"]: 8, other_project["id"]: 1}
    assert everything["total"] == 9 and everything["by_kind"]["work-plan-proposed"] == 2
    scoped = (await client.get(COUNTS, params={"project_id": other_project["id"]})).json()
    assert scoped["total"] == 1 and scoped["by_project"] == {other_project["id"]: 1}
    assert scoped["by_kind"]["work-plan-proposed"] == 1 and scoped["by_kind"]["failed-run"] == 0
    assert [row["kind"] for row in await items(client, project_id=other_project["id"])] == ["work-plan-proposed"]
    assert (await client.get(COUNTS, params={"project_id": str(uuid4())})).status_code == 404


async def test_keyset_pages_filters_and_errors(client, owed, github, session):
    stamp = get_current_utc_time()
    paused = []
    for number in range(30, 35):
        run = await enroll(client, github, owed, number)
        paused.append(run["id"])
    for i in range(100):
        row = await plan(session, owed, state="proposed", title=f"Plan {i}")
        row.updated_at = stamp
    await session.commit()
    for run_id in paused:
        await set_run(session, run_id, state="paused", updated_at=stamp + timedelta(minutes=1))
    first = (await client.get(URL, params={"limit": 100})).json()
    assert len(first["items"]) == 100 and first["has_more"] and first["next_cursor"]
    second = (await client.get(URL, params={"limit": 100, "cursor": first["next_cursor"]})).json()
    assert len(second["items"]) == 5 and not second["has_more"] and second["next_cursor"] is None
    keys = [row["key"] for row in first["items"] + second["items"]]
    assert len(set(keys)) == 105
    ordered = [(row["waiting_since"], row["key"]) for row in first["items"] + second["items"]]
    assert ordered == sorted(ordered)
    assert {row["kind"] for row in second["items"]} == {"stopped-run"}
    # A one-row walk follows the same (waiting_since, key) order, ties included.
    walked, cursor = [], None
    for _ in range(3):
        params = {"limit": 1, **({"cursor": cursor} if cursor else {})}
        step = (await client.get(URL, params=params)).json()
        walked.append(step["items"][0]["key"])
        cursor = step["next_cursor"]
    assert walked == keys[:3]
    assert {row["kind"] for row in await items(client, kind="stopped-run")} == {"stopped-run"}
    assert len(await items(client, kind="stopped-run")) == 5
    assert (await client.get(URL, params={"limit": 101})).status_code == 422
    assert (await client.get(URL, params={"limit": 0})).status_code == 422
    assert (await client.get(URL, params={"kind": "catalog-hold"})).status_code == 422
    assert (await client.get(URL, params={"cursor": "broken"})).status_code == 422
    changed = await client.get(URL, params={"limit": 100, "cursor": first["next_cursor"], "kind": "stopped-run"})
    assert changed.status_code == 422
    assert (await client.get(URL, params={"project_id": str(uuid4())})).status_code == 404


async def test_reads_need_a_signed_in_user(client, app, owed):
    app.dependency_overrides.pop(get_current_user)
    assert (await client.get(URL)).status_code == 401
    assert (await client.get(COUNTS)).status_code == 401


async def test_one_transaction_and_fixed_statements_without_provider_calls(client, owed, github, session):
    async def measure():
        statements, begins = [], []

        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(id(conn))

        def begin(conn):
            begins.append(id(conn))

        event.listen(Engine, "before_cursor_execute", record)
        event.listen(Engine, "begin", begin)
        try:
            measured = {}
            for name, url, params in (
                ("list", URL, {}),
                ("list-project", URL, {"project_id": owed["id"]}),
                ("counts", COUNTS, {}),
                ("counts-project", COUNTS, {"project_id": owed["id"]}),
            ):
                statements.clear()
                begins.clear()
                response = await client.get(url, params=params)
                assert response.status_code == 200, response.text
                # One transaction on one connection per read.
                assert len(begins) == 1 and set(statements) == set(begins), name
                measured[name] = len(statements)
            return measured
        finally:
            event.remove(Engine, "before_cursor_execute", record)
            event.remove(Engine, "begin", begin)

    await every_kind(client, github, session, owed, offset=0)
    github.paths.clear()
    small = await measure()
    await every_kind(client, github, session, owed, offset=1)
    await every_kind(client, github, session, owed, offset=2)
    github.paths.clear()
    large = await measure()
    assert small == large
    assert small == {"list": 1, "list-project": 2, "counts": 1, "counts-project": 2}
    assert len((await client.get(URL, params={"limit": 100})).json()["items"]) == 27
    assert not github.paths


async def test_failed_runs_yield_to_batch_and_work_item_attention(client, owed, github, session):
    batch_run = await enroll(client, github, owed, 7)
    await set_run(session, batch_run["id"], state="failed")
    item_run = await enroll(client, github, owed, 8)
    await set_run(session, item_run["id"], state="failed")
    held = await batch(session, owed, run_id=batch_run["id"], unit="specs/one")
    work = await plan(session, owed)
    attention = await item(session, work, "attention", state="attention", run_id=item_run["id"])
    await session.commit()
    rows = await items(client)
    assert sorted((row["kind"], row["subject"]["id"]) for row in rows) == sorted(
        [("sdd-batch-attention", str(held.id)), ("work-item-attention", str(attention.id))]
    )


async def test_server_default_timestamps_page_without_gaps(client, owed, session):
    # Server defaults store whole seconds; rows sharing that second must survive a page boundary.
    for i in range(5):
        await plan(session, owed, state="proposed", title=f"Same second {i}")
    await session.commit()
    keys, cursor = [], None
    while True:
        params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        page = (await client.get(URL, params=params)).json()
        keys += [row["key"] for row in page["items"]]
        cursor = page["next_cursor"]
        if not page["has_more"]:
            break
    assert len(keys) == len(set(keys)) == 5
