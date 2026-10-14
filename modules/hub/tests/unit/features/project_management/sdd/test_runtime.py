import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import checkout, isolation, runtime
from app.features.project_management.sdd.decisions import validate_answer

pytestmark = pytest.mark.unit


async def test_missing_receipt_never_syncs_or_initializes(tmp_path, monkeypatch):
    invoke = AsyncMock()
    monkeypatch.setattr(checkout, "command", invoke)
    with pytest.raises(ProjectError, match="receipt"):
        await runtime.restore(tmp_path, "fixture")
    invoke.assert_not_awaited()


def test_runtime_pin_detects_changed_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOHUB_SDD_HOME", str(tmp_path))
    (tmp_path / "uv.lock").write_text("original")
    (tmp_path / "pin.json").write_text(
        json.dumps({"provider": "devkit-spec", "lock_sha256": hashlib.sha256(b"original").hexdigest()})
    )
    assert runtime.configured_version().startswith("devkit-spec:")
    (tmp_path / "uv.lock").write_text("different")
    with pytest.raises(ProjectError, match="locked runtime"):
        runtime.configured_version()


async def test_cli_drops_credentials_and_requires_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "private-token")
    monkeypatch.setenv("DATABASE_URL", "private-db")
    monkeypatch.setattr(runtime, "runtime_pin", lambda: {"python_prefix": "/usr"})
    monkeypatch.setattr(runtime, "runtime_home", lambda: Path("/opt/sdd"))
    monkeypatch.setattr(isolation, "isolated_command", lambda *args, **kwargs: ["sandbox", "devkit"])

    async def invoke(*args, **kwargs):
        assert args == ("sandbox", "devkit")
        env = kwargs["env"]
        assert "GH_TOKEN" not in env and "DATABASE_URL" not in env
        assert Path(env["HOME"]).is_relative_to(tmp_path)
        assert kwargs["devkit"]
        return "safe"

    monkeypatch.setattr(checkout, "_command", invoke)
    assert await checkout.command("devkit", "rules", "check", cwd=tmp_path) == "safe"


def test_no_unsandboxed_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(isolation.shutil, "which", lambda _: None)
    with pytest.raises(ProjectError, match="isolated runner"):
        isolation.isolated_command(tmp_path, tmp_path, (), "/usr")


@pytest.mark.parametrize("code", ["RULES_RUN_FAILED", "RECEIPT_STALE", "SELECTION_INVALID"])
async def test_json_diagnostic_never_leaks_repository_text(tmp_path, monkeypatch, code):
    process = AsyncMock()
    process.returncode = 2
    process.communicate.return_value = (
        json.dumps({"error": {"code": code, "message": "secret-token private-path"}}).encode(),
        b"secret stderr",
    )
    monkeypatch.setattr(checkout.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    with pytest.raises(checkout.SddCommandError) as result:
        await checkout._command("sandbox", cwd=tmp_path, env={}, allow_failure=False, devkit=True)
    assert result.value.cli_code == code
    assert "secret" not in result.value.detail and "private-path" not in result.value.detail


def test_handoff_requires_eligible_choice_and_integration_uses_own_authority():
    evidence = {
        "current": {
            "requests": [
                {
                    "id": "handoff",
                    "kind": "choose",
                    "options": [{"id": "direct", "eligible": True}, {"id": "bad", "eligible": False}],
                }
            ]
        }
    }
    assert validate_answer(evidence, {"request": "handoff", "action": "accept", "value": "direct"})
    with pytest.raises(ProjectError, match="eligible"):
        validate_answer(evidence, {"request": "handoff", "action": "accept", "value": "bad"})
    assert validate_answer(evidence, {"request": "handoff", "action": "cancel"})
    evidence["current"]["requests"] = [{"id": "gate:integration", "kind": "approve"}]
    with pytest.raises(ProjectError, match="integration approval"):
        validate_answer(evidence, {"request": "gate:integration", "action": "accept"})
