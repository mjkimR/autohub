import json
import shutil
import subprocess
from uuid import UUID

import pytest
from app.features.execution.flows import bridge
from app.features.execution.flows.adapters import WorkerBindings, get_worker_bindings
from app.features.execution.flows.bridge_config import DeliveryTarget
from app.features.execution.flows.evidence import BridgeRejected, read_evidence
from app.features.execution.flows.models import FlowPRLink
from app.features.execution.flows.worker import FlowWorker
from app.features.project_management.pipeline_runs.models import PipelineRun, RunResumeReceipt
from autohub_sdk import (
    ApprovalStep,
    FlowManifest,
    FlowSpec,
    InputRef,
    PipelineSpec,
    ReleaseSpec,
    TaskBinding,
    TaskRef,
    TaskStep,
)
from sqlalchemy import select, update
from tests.integration.features.execution.flows.test_host import RELEASE_PATH, RUNS, command, get
from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

pytestmark = pytest.mark.real_commit
github = scenarios.github
project = scenarios.project
SPEC = "specs/2026-10/20261009-fixture"


@pytest.fixture
def checkout(tmp_path):
    if shutil.which("specrig") is None:
        pytest.skip("native specrig adapter requires installed CLI")
    root = tmp_path / "checkout"
    root.mkdir()

    def run(*args):
        return subprocess.check_output(args, cwd=root, text=True, stderr=subprocess.DEVNULL).strip()

    run("git", "init", "-q")
    (root / ".gitignore").write_text(".agents/\n.claude/\n.codex/\n.specrig/.cache/\n")
    run("specrig", "init", "--skip-agents")
    workflow = root / ".specrig/workflows/bridge-test.md"
    base = {"artifacts": [], "skills": [], "role": "developer", "isolation": "none", "returns": []}
    schema = {
        "id": "WF-bridge-test",
        "title": "Fixture evidence gate",
        "status": "active",
        "schema_version": 1,
        "stages": [
            {
                **base,
                "id": "bridge-check",
                "name": "Evidence",
                "human_gate": False,
                "entry": ["spec-dir-exists"],
                "exit": [
                    "envelope-review-passed",
                    "reconcile-resolved",
                    "spec-status-completed",
                    "envelope-final-report-present",
                ],
            },
            {
                **base,
                "id": "bridge-approval",
                "name": "Approval",
                "human_gate": True,
                "entry": ["envelope-final-report-present"],
                "exit": ["approval-given"],
            },
        ],
    }
    workflow.write_text("---\n" + json.dumps(schema) + "\n---\n")
    spec = root / SPEC
    (spec / "envelopes").mkdir(parents=True)
    (spec / "spec.md").write_text(
        "---\nid: SPEC-fixture\ntitle: Fixture\nstatus: completed\ncreated: 2026-10-09\n---\n# Fixture\n"
    )
    (spec / "reconcile.md").write_text(
        "---\nreconcile_id: REC-fixture\nstatus: resolved\ntargets: []\n---\n# No living changes\n"
    )
    for kind in ("review", "final-report"):
        (spec / f"envelopes/{kind}-01.yaml").write_text(
            f"kind: {kind}\nstatus: completed\nsummary: Fixture verified\nchecks:\n  tests: PASS fixture\n  build: PASS fixture\n  lint: PASS fixture\n"
        )
    run("specrig", "workflow", "bind", "--spec", SPEC, "--workflow", ".specrig/workflows/bridge-test.md")
    run("git", "add", ".")
    run("git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com", "commit", "-qm", "Fixture")
    return root, run("git", "rev-parse", "HEAD")


@pytest.fixture
async def paused(client, project, github, checkout, credential_key_provider, monkeypatch, clock):
    root, head = checkout
    github.pulls[7]["head"]["sha"] = head
    response = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7, "implemented": True})
    assert response.status_code == 201, response.text
    pipeline = response.json()
    pipeline = (await client.post(f"/api/v1/pipeline-runs/{pipeline['id']}/pause")).json()
    monkeypatch.setattr(bridge, "get_credential_key_provider", lambda: credential_key_provider)
    monkeypatch.setattr(bridge, "get_current_utc_time", lambda: clock.now)
    return pipeline, root, head


def release(with_approval=True):
    schema = {"type": "object"}
    check = PipelineSpec(
        key="planhub.workflow_check",
        contract_version=1,
        title="Check",
        description="",
        input_schema=schema,
        output_schema=schema,
    )
    deliver = PipelineSpec(
        key="planhub.pr_delivery",
        contract_version=1,
        title="Deliver",
        description="",
        input_schema=schema,
        output_schema=schema,
    )
    names = ("pipeline_run_id", "pipeline_revision", "head_sha", "spec_dir")
    flow = FlowSpec(
        key="planhub.delivery",
        title="Deliver",
        input_schema=schema,
        output_schema=schema,
        result_step="deliver",
        steps=(
            TaskStep(
                id="check",
                task=TaskRef(key=check.key),
                inputs={key: InputRef(source="run", path=(key,)) for key in names},
            ),
            ApprovalStep(id="approve"),
            TaskStep(
                id="deliver",
                task=TaskRef(key=deliver.key),
                inputs={
                    key: InputRef(source="step", step_id="check", path=(key,)) for key in (*names, "evidence_digest")
                },
            ),
        ),
    )
    if not with_approval:
        flow = flow.model_copy(
            update={"steps": tuple(step for step in flow.steps if not isinstance(step, ApprovalStep))}
        )
    return ReleaseSpec(
        manifest=FlowManifest(tasks=(check, deliver), flows=(flow,)),
        bindings=(
            TaskBinding(task=TaskRef(key=check.key), executor="native", target="autohub.specrig:local"),
            TaskBinding(task=TaskRef(key=deliver.key), executor="native", target="autohub.pr_delivery:local"),
        ),
    )


async def setup(client, app, paused, with_approval=True):
    pipeline, root, head = paused
    target = DeliveryTarget(provider="planhub", environment="local", project_id=pipeline["project_id"], checkout=root)
    app.dependency_overrides[get_worker_bindings] = lambda: WorkerBindings(deliveries={"local": target})
    spec = release(with_approval)
    response = await client.put(RELEASE_PATH, json=spec.model_dump(mode="json"))
    assert response.status_code == 200, response.text
    assert (await client.post(RELEASE_PATH + "/activate", json={"expected_revision": 0})).status_code == 200
    response = await client.post(
        RUNS,
        json={
            "provider": "planhub",
            "environment": "local",
            "task": {"key": "planhub.delivery"},
            "inputs": {
                "pipeline_run_id": pipeline["id"],
                "pipeline_revision": pipeline["revision"],
                "head_sha": head,
                "spec_dir": SPEC,
            },
            "idempotency_key": "bridge-1",
            "expected_release_id": "release-1",
            "expected_release_digest": spec.digest(),
        },
    )
    assert response.status_code == 202, response.text
    return response.json()


async def approval(client, run):
    await FlowWorker().advance(UUID(run["run_id"]))
    await FlowWorker().advance(UUID(run["run_id"]))
    run = await get(client, run)
    assert run["waiting_reason"] == "approval", run
    response = await command(client, run, "approve")
    assert response.status_code == 200, response.text
    return response.json()


async def test_real_git_cli_evidence_rejects_dirty_and_changed_head(checkout):
    root, head = checkout
    digest = await read_evidence(str(root), SPEC, head)
    assert len(digest) == 64
    (root / SPEC / "envelopes/review-01.yaml").write_text("kind: review\nstatus: failed\n")
    with pytest.raises(BridgeRejected, match="checkout-dirty"):
        await read_evidence(str(root), SPEC, head)
    with pytest.raises(BridgeRejected, match="checkout-head-changed"):
        await read_evidence(str(root), SPEC, "0" * 40)


async def test_bridge_resumes_once_then_observes_existing_pr(client, owner, app, paused, clock, session_maker):
    run = await setup(client, app, paused)
    run = await approval(client, run)
    await FlowWorker().advance(UUID(run["run_id"]))
    waiting = await get(client, run)
    assert waiting["status"] == "waiting"
    async with session_maker() as session:
        [link] = list(await session.scalars(select(FlowPRLink)))
        receipts = list(await session.scalars(select(RunResumeReceipt)))
        assert len(receipts) == 1 and receipts[0].id == link.delivery_attempt_id
        assert link.approved_revision is not None and link.approved_actor
        assert link.approved_digest is not None
        assert (await session.get(PipelineRun, UUID(paused[0]["id"]))).state == "awaiting_ci"
    clock.advance()
    await FlowWorker().advance(UUID(run["run_id"]))
    async with session_maker() as session:
        assert len(list(await session.scalars(select(RunResumeReceipt)))) == 1
        await session.execute(
            update(PipelineRun).where(PipelineRun.id == UUID(paused[0]["id"])).values(state="completed")
        )
        await session.commit()
    clock.advance()
    await FlowWorker().advance(UUID(run["run_id"]))
    await FlowWorker().advance(UUID(run["run_id"]))
    done = await get(client, run)
    assert done["status"] == "completed" and done["output"]["pipeline_run_id"] == paused[0]["id"]


@pytest.mark.parametrize("state", ["paused", "blocked", "failed", "canceled"])
async def test_pr_owner_state_is_projected(client, owner, app, paused, clock, session_maker, state):
    run = await approval(client, await setup(client, app, paused))
    await FlowWorker().advance(UUID(run["run_id"]))
    async with session_maker() as session:
        await session.execute(update(PipelineRun).where(PipelineRun.id == UUID(paused[0]["id"])).values(state=state))
        await session.commit()
    clock.advance()
    await FlowWorker().advance(UUID(run["run_id"]))
    projected = await get(client, run)
    assert projected["error"] == f"pr-{state}"
    assert projected["status"] == ("waiting" if state in ("paused", "blocked") else "failed")
    assert projected["attempts"][-1]["output"]["state"] == state


async def test_approval_head_change_rejects_resume(client, owner, app, paused, github, session_maker):
    run = await approval(client, await setup(client, app, paused))
    github.pulls[7]["head"]["sha"] = "b" * 40
    await FlowWorker().advance(UUID(run["run_id"]))
    failed = await get(client, run)
    assert failed["status"] == "failed" and failed["error"] == "pr-resume-rejected"
    async with session_maker() as session:
        assert (await session.get(PipelineRun, UUID(paused[0]["id"]))).state == "paused"
        assert list(await session.scalars(select(RunResumeReceipt))) == []


async def test_approval_evidence_change_and_cancel_fence(client, owner, app, paused, clock, session_maker):
    run = await approval(client, await setup(client, app, paused))
    root = paused[1]
    (root / SPEC / "envelopes/final-report-01.yaml").write_text(
        "kind: final-report\nstatus: completed\nsummary: Changed after approval\n"
    )
    await FlowWorker().advance(UUID(run["run_id"]))
    failed = await get(client, run)
    assert failed["status"] == "failed" and failed["error"] == "checkout-dirty"
    canceled = await command(client, failed, "cancel")
    assert canceled.status_code == 200
    async with session_maker() as session:
        assert (await session.get(PipelineRun, UUID(paused[0]["id"]))).state == "paused"


async def test_native_bridge_requires_persisted_scoped_approval(client, owner, app, paused, session_maker):
    run = await setup(client, app, paused, with_approval=False)
    await FlowWorker().advance(UUID(run["run_id"]))
    await FlowWorker().advance(UUID(run["run_id"]))
    failed = await get(client, run)
    assert failed["error"] == "pr-resume-approval-required"
    async with session_maker() as session:
        assert (await session.get(PipelineRun, UUID(paused[0]["id"]))).state == "paused"
        assert list(await session.scalars(select(RunResumeReceipt))) == []


async def test_one_flow_claims_pipeline_and_native_namespace_is_restricted(client, owner, app, paused):
    from app.features.execution.flows.errors import FlowError

    run = await setup(client, app, paused)
    await FlowWorker().advance(UUID(run["run_id"]))
    first = await get(client, run)
    body = {
        "provider": "planhub",
        "environment": "local",
        "task": {"key": "planhub.delivery"},
        "inputs": first["attempts"][0]["inputs"],
        "idempotency_key": "other-plan",
    }
    other = (await client.post(RUNS, json=body)).json()
    await FlowWorker().advance(UUID(other["run_id"]))
    assert (await get(client, other))["error"] == "pr-owned-by-another-flow"
    target = DeliveryTarget(
        provider="planhub", environment="local", project_id=paused[0]["project_id"], checkout=paused[1]
    )
    with pytest.raises(FlowError):
        WorkerBindings(deliveries={"local": target}).resolve(release(), "other", "local")


async def test_pr_resume_effect_survives_worker_death_and_cancel_fences_owner(
    client, owner, app, paused, clock, session_maker
):
    from app.features.execution.flows.adapters import WorkerAdapter

    run = await approval(client, await setup(client, app, paused))

    class ProcessDeath(BaseException):
        pass

    class Crash(WorkerAdapter):
        async def execute(self, action):
            await super().execute(action)
            raise ProcessDeath()

    with pytest.raises(ProcessDeath):
        await FlowWorker(Crash()).advance(UUID(run["run_id"]))
    clock.advance()
    await FlowWorker().advance(UUID(run["run_id"]))
    pending = await get(client, run)
    async with session_maker() as session:
        assert len(list(await session.scalars(select(RunResumeReceipt)))) == 1
    assert (await command(client, pending, "cancel")).json()["status"] == "canceling"
    clock.advance()
    await FlowWorker().advance(UUID(run["run_id"]))
    assert (await get(client, run))["status"] == "canceled"
    async with session_maker() as session:
        assert (await session.get(PipelineRun, UUID(paused[0]["id"]))).state == "canceled"
        assert (await session.get(FlowPRLink, UUID(paused[0]["id"]))).canceled is True
