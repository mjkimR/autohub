"""Workflow pins: semantic, stable across checkouts and blind to diagnostic notices."""

from typing import Any

import pytest

pytestmark = pytest.mark.unit


def test_workflow_pin_is_stable_across_checkouts_but_covers_effective_semantics():
    from app.features.project_management.sdd.contracts import workflow_hash

    definition = {
        "id": "workflow",
        "stages": [{"id": "review", "exit": ["checked"]}],
        "approvals": {"integration": "ask"},
    }
    expected = workflow_hash(definition)
    assert (
        workflow_hash({**definition, "path": "/tmp/one/workflow.md", "binding": {"workflow": "workflow"}}) == expected
    )
    assert workflow_hash({**definition, "path": "/tmp/two/workflow.md", "ok": True, "errors": []}) == expected
    assert workflow_hash({**definition, "approvals": {"integration": "auto"}}) != expected
    assert workflow_hash({**definition, "stages": [{"id": "review", "exit": []}]}) != expected


def test_workflow_notices_do_not_change_the_existing_semantic_hash():
    from app.features.project_management.sdd.contracts import workflow_hash

    definition = {"id": "workflow", "stages": [{"id": "review", "exit": ["checked"]}]}
    expected = workflow_hash(definition)
    assert workflow_hash({**definition, "notices": []}) == expected
    assert workflow_hash({**definition, "notices": [{"message": "volatile warning"}]}) == expected
    assert workflow_hash({**definition, "stages": []}) != expected


async def test_bridge_evidence_reports_a_preparing_runtime_as_retryable(tmp_path, monkeypatch):
    """SDD_RUNTIME_PREPARING propagates (bridge-unavailable) instead of a terminal evaluation rejection."""
    from app.features.execution.flows import evidence
    from app.features.project_management.projects.errors import ProjectError
    from app.features.project_management.sdd import services

    spec = tmp_path / "specs/2026-11/demo"
    spec.mkdir(parents=True)

    async def process(*args, cwd):
        return "a" * 40 if "rev-parse" in args else ""

    async def evaluate(self, *args):
        raise ProjectError(503, "installing", code="SDD_RUNTIME_PREPARING")

    monkeypatch.setattr(evidence, "process", process)
    monkeypatch.setattr(services.SddService, "evaluate", evaluate)
    with pytest.raises(ProjectError) as raised:
        await evidence.read_evidence(str(tmp_path), "specs/2026-11/demo", "a" * 40)
    assert raised.value.code == "SDD_RUNTIME_PREPARING"


@pytest.mark.parametrize("terminal", [False, True])
async def test_bridge_worker_retries_preparing_and_fails_other_evaluation_errors(monkeypatch, terminal):
    from types import SimpleNamespace
    from uuid import uuid4

    from app.features.execution.flows import bridge
    from app.features.execution.flows.errors import FlowError
    from app.features.project_management.projects.errors import ProjectError

    async def check(self, action, data):
        if terminal:  # read_evidence turns a non-retryable evaluation refusal into this rejection
            raise bridge.BridgeRejected("workflow-evaluation-failed")
        raise ProjectError(503, "installing", code="SDD_RUNTIME_PREPARING")

    monkeypatch.setattr(bridge.PRBridgeWorker, "check", check)
    monkeypatch.setattr(bridge.BridgeInputs, "model_validate", classmethod(lambda cls, value: SimpleNamespace()))
    action: Any = SimpleNamespace(
        inputs={}, binding={"target": "autohub.sdd:local"}, operation="submit", attempt_id=str(uuid4())
    )
    worker = bridge.PRBridgeWorker.__new__(bridge.PRBridgeWorker)
    if terminal:
        result = await worker.execute(action)
        assert result.status == "failed" and result.error == "workflow-evaluation-failed"
    else:
        with pytest.raises(FlowError) as raised:
            await worker.execute(action)
        assert raised.value.status == 503 and raised.value.code == "bridge-unavailable"


async def test_bridge_evidence_keeps_host_misconfiguration_terminal(tmp_path, monkeypatch):
    from app.features.execution.flows import evidence
    from app.features.execution.flows.bridge import BridgeRejected
    from app.features.project_management.projects.errors import ProjectError
    from app.features.project_management.sdd import services

    (tmp_path / "specs/2026-11/demo").mkdir(parents=True)

    async def process(*args, cwd):
        return "a" * 40 if "rev-parse" in args else ""

    async def evaluate(self, *args):
        raise ProjectError(503, "no uv", code="SDD_RUNTIME_UNAVAILABLE")

    monkeypatch.setattr(evidence, "process", process)
    monkeypatch.setattr(services.SddService, "evaluate", evaluate)
    with pytest.raises(BridgeRejected, match="workflow-evaluation-failed"):
        await evidence.read_evidence(str(tmp_path), "specs/2026-11/demo", "a" * 40)
