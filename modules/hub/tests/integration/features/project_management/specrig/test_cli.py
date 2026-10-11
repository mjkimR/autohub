"""Use real Git and installed specrig, including policy and version pins."""

import json
import subprocess

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.specrig.services import SpecrigService
from tests.integration.features.execution.flows import test_bridge

SPEC = test_bridge.SPEC
checkout = test_bridge.checkout

pytestmark = pytest.mark.integration


async def test_real_cli_reads_gate_and_rejects_changed_version(checkout, monkeypatch):
    root, head = checkout
    version = subprocess.check_output(["specrig", "--version"], text=True).strip()
    monkeypatch.setenv("AUTOHUB_SPECRIG_VERSION", version)
    service = SpecrigService()
    evidence = await service.evaluate(root, SPEC, head, head, None, False)
    assert evidence["current"]["stage"]["human_gate"]
    assert not evidence["integrated"]
    assert evidence["snapshot"]["policy"]["workflow.approvals.integration"] == "ask"
    with pytest.raises(ProjectError, match="version"):
        await service.evaluate(root, SPEC, head, head, {**evidence["snapshot"], "cli_version": "unsupported"}, False)
    with pytest.raises(ProjectError, match="workflow or policy"):
        await service.evaluate(root, SPEC, head, head, {**evidence["snapshot"], "workflow_hash": "changed"}, False)


async def test_real_cli_final_lint_and_no_change_integration(checkout, monkeypatch):
    root, _ = checkout
    workflow = root / ".specrig/workflows/bridge-test.md"
    schema = json.loads(workflow.read_text().split("---")[1])
    common = {
        "artifacts": [],
        "skills": [],
        "role": "developer",
        "isolation": "none",
        "returns": [],
        "human_gate": False,
    }
    schema["stages"].extend(
        [
            {
                **common,
                "id": "fixture-integrate",
                "name": "Integrate",
                "entry": ["approval-given"],
                "exit": ["lint-ci-clean"],
            },
            {**common, "id": "fixture-merge", "name": "Merge", "entry": ["lint-ci-clean"], "exit": ["merged"]},
        ]
    )
    workflow.write_text("---\n" + json.dumps(schema) + "\n---\n")

    def run(*args):
        return subprocess.check_output(args, cwd=root, text=True, stderr=subprocess.DEVNULL).strip()

    run("specrig", "workflow", "bind", "--spec", SPEC, "--workflow", ".specrig/workflows/bridge-test.md")
    run("git", "add", ".")
    run("git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com", "commit", "-qm", "Extend fixture")
    head = run("git", "rev-parse", "HEAD")
    monkeypatch.setenv("AUTOHUB_SPECRIG_VERSION", run("specrig", "--version"))
    evidence = await SpecrigService().evaluate(root, SPEC, head, head, None, True)
    assert evidence["integrated"]
    assert evidence["current"]["stage"]["id"] == "fixture-merge"
    assert evidence["head_sha"] == evidence["base_sha"] == head
