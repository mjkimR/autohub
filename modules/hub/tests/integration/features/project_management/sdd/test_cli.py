"""Use real Git and installed sdd, including policy and version pins."""

import json
import os
import subprocess

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd.services import SddService
from tests.integration.features.execution.flows import test_bridge

SPEC = test_bridge.SPEC
checkout = test_bridge.checkout

pytestmark = pytest.mark.integration


async def test_real_cli_reads_gate_and_rejects_changed_version(checkout, monkeypatch):
    root, head = checkout
    version = __import__(
        "app.features.project_management.sdd.runtime", fromlist=["configured_version"]
    ).configured_version()
    monkeypatch.setenv("AUTOHUB_SDD_VERSION", version)
    service = SddService()
    evidence = await service.evaluate(root, SPEC, head, head, None, False)
    assert evidence["current"]["stage"]["human_gate"]
    assert not evidence["integrated"]
    assert evidence["snapshot"]["policy"]["approvals"]["integration"]["policy"] == "ask"
    with pytest.raises(ProjectError, match="version"):
        await service.evaluate(root, SPEC, head, head, {**evidence["snapshot"], "cli_version": "unsupported"}, False)
    with pytest.raises(ProjectError, match="workflow or policy"):
        await service.evaluate(root, SPEC, head, head, {**evidence["snapshot"], "workflow_hash": "changed"}, False)


async def test_real_cli_final_lint_and_no_change_integration(checkout, monkeypatch):
    root, _ = checkout
    workflow = root / ".devkit/workflows/bridge-test.md"
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
                "entry": [],
                "exit": ["lint-ci-clean"],
            },
            {**common, "id": "fixture-merge", "name": "Merge", "entry": ["lint-ci-clean"], "exit": ["merged"]},
        ]
    )
    workflow.write_text("---\n" + json.dumps(schema) + "\n---\n")

    def run(*args):
        return subprocess.check_output(args, cwd=root, text=True, stderr=subprocess.DEVNULL).strip()

    run(
        str(__import__("pathlib").Path(os.environ["AUTOHUB_SDD_HOME"]) / ".venv/bin/devkit"),
        "workflow",
        "bind",
        "--unit",
        SPEC,
        "--workflow",
        str(workflow.relative_to(root)),
    )
    run("git", "add", ".")
    run("git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com", "commit", "-qm", "Extend fixture")
    head = run("git", "rev-parse", "HEAD")
    monkeypatch.setenv(
        "AUTOHUB_SDD_VERSION",
        run(str(__import__("pathlib").Path(os.environ["AUTOHUB_SDD_HOME"]) / ".venv/bin/devkit"), "--version"),
    )
    evidence = await SddService().evaluate(root, SPEC, head, head, None, True)
    assert evidence["integrated"]
    assert evidence["current"]["stage"]["id"] == "fixture-merge"
    assert evidence["head_sha"] == evidence["base_sha"] == head


async def test_fresh_checkout_restores_recorded_release_without_network(checkout, tmp_path, monkeypatch):

    root, _ = checkout
    if not os.environ.get("AUTOHUB_SDD_HOME"):
        if os.environ.get("AUTOHUB_REQUIRE_SDD"):
            pytest.fail("required release runtime was not provisioned")
        pytest.skip("fresh release restore requires just test-sdd")
    fresh = (tmp_path / "fresh").resolve()
    subprocess.run(["git", "clone", "--quiet", str(root), str(fresh)], check=True)
    manifest = fresh / ".devkit/installation.json"
    original = manifest.read_bytes()
    assert not (fresh / ".devkit/managed").exists()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=fresh, text=True).strip()
    result = await SddService().evaluate(fresh, SPEC, head, head, None, False)
    assert result["current"]["stage"]["human_gate"]
    assert result["reports"][0]["kind"] == "final-report"
    assert result["reports"][0]["summary"] == "Fixture verified"
    assert manifest.read_bytes() == original
    assert (fresh / ".devkit/managed/spec/workflows/direct-delivery.md").is_file()
    assert not subprocess.check_output(["git", "diff", "--name-only"], cwd=fresh, text=True).strip()


async def test_devkit_authors_answer_and_return_and_invalidates_approval(checkout):
    from app.features.project_management.sdd.decisions import prepare_record
    from app.features.project_management.sdd.services import cli

    root, _ = checkout
    operation = {"id": "a-fixed-receipt", "request": "gate:integration", "action": "accept", "actor": "user:fixture"}
    record = await prepare_record(root, SPEC, operation, cli)
    assert record["file"].startswith("decisions/")
    assert "autohub-decision:a-fixed-receipt" in record["content"]
    current = await cli(root, "workflow", "next", "--unit", SPEC)
    assert current["complete"]
    await prepare_record(
        root, SPEC, {"id": "return-receipt", "return_to": "bridge-approval", "actor": "user:fixture"}, cli
    )
    current = await cli(root, "workflow", "next", "--unit", SPEC)
    assert current["requests"][0]["id"] == "gate:integration"
    assert not current["complete"]


async def test_python_check_cannot_read_host_secret_or_use_network(checkout, tmp_path, monkeypatch):
    from app.features.project_management.sdd.services import cli

    root, _ = checkout
    secret = tmp_path / "server-secret.txt"
    secret.write_text("must-not-leak")
    monkeypatch.setenv("SDD_TEST_SECRET", "must-not-leak")
    plugin = root / ".devkit/workflow-checks/probe"
    plugin.mkdir(parents=True)
    plugin.joinpath("__init__.py").write_text(
        "import json, os, socket\nfrom pathlib import Path\n"
        f"try:\n data = Path({str(secret)!r}).read_text()\nexcept OSError:\n data = 'denied'\n"
        "try:\n socket.create_connection(('127.0.0.1', 9), timeout=1)\n network = 'allowed'\n"
        "except OSError as exc:\n network = exc.errno\n"
        "Path('probe.json').write_text(json.dumps({'file': data, 'env': os.environ.get('SDD_TEST_SECRET'), 'network': network}))\n"
    )
    await cli(root, "workflow", "checks")
    probe = json.loads((root / "probe.json").read_text())
    assert probe["file"] == "denied"
    assert probe["env"] is None
    assert probe["network"] in (1, 13, 101)  # EPERM/EACCES, or ENETUNREACH in a fresh Linux network namespace


async def test_accepted_handoff_authorizes_only_the_selected_definition(checkout):
    from app.features.project_management.sdd.decisions import prepare_record
    from app.features.project_management.sdd.services import cli

    root, _ = checkout
    path = root / ".devkit/workflows/bridge-test.md"
    definition = json.loads(path.read_text().split("---")[1])
    successor = {
        **definition,
        "id": "delivery-successor",
        "title": "Successor",
        "stages": [{**definition["stages"][-1], "id": "successor-approval"}],
    }
    target = root / ".devkit/workflows/successor.md"
    target.write_text("---\n" + json.dumps(successor) + "\n---\n")
    definition["next"] = [{"workflow": "delivery-successor", "when": [], "recommended": True}]
    path.write_text("---\n" + json.dumps(definition) + "\n---\n")
    from app.features.project_management.sdd.checkout import command

    await command("devkit", "workflow", "bind", "--unit", SPEC, "--workflow", "bridge-test", cwd=root)
    await prepare_record(
        root, SPEC, {"id": "g3", "request": "gate:integration", "action": "accept", "actor": "user:fixture"}, cli
    )
    before = await SddService().evaluate(root, SPEC, "head", "base", None, False)
    assert before["current"]["requests"][0]["id"] == "handoff"
    record = await prepare_record(
        root,
        SPEC,
        {
            "id": "handoff",
            "request": "handoff",
            "action": "accept",
            "value": "delivery-successor",
            "actor": "user:fixture",
        },
        cli,
    )
    await cli(root, "workflow", "handoff", "--unit", SPEC)
    with pytest.raises(ProjectError, match="workflow or policy"):
        await SddService().evaluate(root, SPEC, "head", "base", before["snapshot"], False)
    snapshot = {**before["snapshot"], "authorized_workflows": [record["authorized_workflow"]]}
    after = await SddService().evaluate(root, SPEC, "head", "base", snapshot, False)
    assert after["current"]["requests"][0]["id"] == "gate:integration"
    assert after["current"]["stage"]["id"] == "successor-approval"
