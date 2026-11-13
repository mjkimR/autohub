"""Workflow pins: semantic, stable across checkouts and blind to diagnostic notices."""

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
