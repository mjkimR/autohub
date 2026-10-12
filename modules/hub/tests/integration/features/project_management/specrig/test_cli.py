"""Use real Git and installed specrig, including policy and version pins."""

import json
import os
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
    receipt = json.loads((root / ".specrig/installation.json").read_text())
    workflow_dir = ".specrig/local/workflows" if receipt.get("layout") == "layered" else ".specrig/workflows"
    workflow = root / workflow_dir / "bridge-test.md"
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

    run("specrig", "workflow", "bind", "--spec", SPEC, "--workflow", str(workflow.relative_to(root)))
    run("git", "add", ".")
    run("git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com", "commit", "-qm", "Extend fixture")
    head = run("git", "rev-parse", "HEAD")
    monkeypatch.setenv("AUTOHUB_SPECRIG_VERSION", run("specrig", "--version"))
    evidence = await SpecrigService().evaluate(root, SPEC, head, head, None, True)
    assert evidence["integrated"]
    assert evidence["current"]["stage"]["id"] == "fixture-merge"
    assert evidence["head_sha"] == evidence["base_sha"] == head


async def test_fresh_checkout_restores_recorded_release_without_network(checkout, tmp_path, monkeypatch):
    from app.features.project_management.specrig.runtime import runtime_home

    root, _ = checkout
    if not os.environ.get("AUTOHUB_SPECRIG_HOME"):
        if os.environ.get("AUTOHUB_REQUIRE_SPECRIG"):
            pytest.fail("required release runtime was not provisioned")
        pytest.skip("fresh release restore requires just test-specrig")
    pin = json.loads((runtime_home() / "pin.json").read_text())
    subprocess.run(
        [
            "specrig",
            "installation",
            "restore",
            str(root),
            "--repository",
            pin["repository"],
            "--cache-dir",
            str(runtime_home() / "releases"),
            "--offline",
            "--json",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.com",
            "commit",
            "--allow-empty",
            "-qm",
            "Record release",
        ],
        cwd=root,
        check=True,
    )
    fresh = (tmp_path / "fresh").resolve()
    subprocess.run(["git", "clone", "--quiet", str(root), str(fresh)], check=True)
    manifest = fresh / ".specrig/installation.json"
    original = manifest.read_bytes()
    receipt = json.loads(original)
    if receipt.get("layout") == "layered":
        assert not (fresh / ".specrig/managed").exists()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=fresh, text=True).strip()
    monkeypatch.setenv("AUTOHUB_SPECRIG_VERSION", f"specrig version {pin['version']} commit={pin['commit']}")
    result = await SpecrigService().evaluate(fresh, SPEC, head, head, None, False)
    assert result["current"]["stage"]["human_gate"]
    assert result["reports"][0]["kind"] == "final-report"
    assert result["reports"][0]["summary"] == "Fixture verified"
    assert manifest.read_bytes() == original
    if receipt.get("layout") == "layered":
        assert (fresh / ".specrig/managed/core/workflows/direct-delivery.md").is_file()
    assert not subprocess.check_output(["git", "diff", "--name-only"], cwd=fresh, text=True).strip()


async def test_real_cli_custom_rules_are_setup_failure_not_repair_work(checkout):
    from app.features.project_management.specrig.checkout import SpecrigCommandError, command

    root, _ = checkout
    receipt = json.loads((root / ".specrig/installation.json").read_text())
    rules = ".specrig/local/rules" if receipt.get("layout") == "layered" else ".specrig/governance/rules"
    custom = root / rules / "custom.go"
    custom.parent.mkdir(parents=True, exist_ok=True)
    custom.write_text("package main\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.com",
            "commit",
            "-qm",
            "Custom rule fixture",
        ],
        cwd=root,
        check=True,
    )
    with pytest.raises(SpecrigCommandError) as result:
        await command("specrig", "lint", "--ci", "--base", "HEAD", cwd=root)
    assert result.value.cli_code == "CUSTOM_RULES_REQUIRE_GO"
