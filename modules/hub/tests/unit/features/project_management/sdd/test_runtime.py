import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import checkout, isolation, runtime
from app.features.project_management.sdd.decisions import validate_answer

pytestmark = pytest.mark.unit


def provision(home: Path, monkeypatch, **extra):
    home.mkdir()
    monkeypatch.setenv("AUTOHUB_SDD_HOME", str(home))
    (home / "uv.lock").write_text("lock")
    pin = {"provider": "devkit-spec", "lock_sha256": hashlib.sha256(b"lock").hexdigest(), **extra}
    (home / "pin.json").write_text(json.dumps(pin))


def lock(revision: str, name: str = "devkit-spec") -> str:
    return f'[[package]]\nname = "{name}"\nversion = "0.1.0"\nsource = {{ git = "https://host/repo?rev=main#{revision}" }}\n'


async def test_missing_receipt_never_syncs_or_initializes(tmp_path, monkeypatch):
    invoke = AsyncMock()
    monkeypatch.setattr(checkout, "command", invoke)
    with pytest.raises(ProjectError, match="receipt"):
        await runtime.restore(tmp_path)
    invoke.assert_not_awaited()


async def test_stale_receipt_is_regenerated_best_effort_and_reported(tmp_path, monkeypatch):
    provision(tmp_path / "runtime", monkeypatch, revisions={"devkit-spec": "f" * 40})
    (tmp_path / ".devkit").mkdir()
    (tmp_path / ".devkit/installation.json").write_text("{}")
    calls = []

    async def invoke(*args, cwd, **kwargs):
        calls.append(args)
        if "--locked" in args:
            raise checkout.SddCommandError("RECEIPT_STALE", "stale")
        return "{}"

    monkeypatch.setattr(checkout, "command", invoke)
    warnings = await runtime.restore(tmp_path)
    assert [item["code"] for item in warnings] == ["RECEIPT_STALE"]
    assert "(devkit-spec ffffffffffff)" in warnings[0]["detail"]
    assert calls == [("devkit", "sync", "--locked", "--format", "json"), ("devkit", "sync", "--format", "json")]


def test_reviewed_runtime_lock_resolves_full_revisions_for_every_compared_package():
    lock = Path(__file__).resolve().parents[7] / "config/sdd-runtime/uv.lock"
    revisions = runtime.lock_revisions(lock.read_text())
    assert set(revisions) == set(runtime.PINNED_PACKAGES)  # the installer records exactly these full revisions


async def test_stale_warning_names_the_runtime_revision_when_recorded(tmp_path, monkeypatch):
    provision(tmp_path / "runtime", monkeypatch, revisions={"devkit-spec": "f" * 40})
    assert "(devkit-spec ffffffffffff)" in runtime.stale_warning()["detail"]
    monkeypatch.setenv("AUTOHUB_SDD_HOME", str(tmp_path / "absent"))
    assert runtime.stale_warning()["code"] == "RECEIPT_STALE"  # no runtime detail, still a warning


async def test_failed_regeneration_after_a_stale_receipt_blocks(tmp_path, monkeypatch):
    (tmp_path / ".devkit").mkdir()
    (tmp_path / ".devkit/installation.json").write_text("{}")
    errors = iter([checkout.SddCommandError("RECEIPT_STALE", "stale"), checkout.SddCommandError("SYNC_CONFLICT", "x")])

    async def invoke(*args, cwd, **kwargs):
        raise next(errors)

    monkeypatch.setattr(checkout, "command", invoke)
    with pytest.raises(checkout.SddCommandError) as result:
        await runtime.restore(tmp_path)
    assert result.value.cli_code == "SYNC_CONFLICT"


@pytest.mark.parametrize("code", ["SELECTION_INVALID", "SYNC_CONFLICT", "COMMAND_FAILED"])
async def test_other_sync_failures_still_block(tmp_path, monkeypatch, code):
    (tmp_path / ".devkit").mkdir()
    (tmp_path / ".devkit/installation.json").write_text("{}")
    invoke = AsyncMock(side_effect=checkout.SddCommandError(code, "failed"))
    monkeypatch.setattr(checkout, "command", invoke)
    with pytest.raises(checkout.SddCommandError) as result:
        await runtime.restore(tmp_path)
    assert result.value.cli_code == code
    assert invoke.await_count == 1


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


def test_revision_mismatch_is_a_warning_without_repository_text(tmp_path, monkeypatch):
    provision(tmp_path / "runtime", monkeypatch, revisions={"devkit-spec": "a" * 40, "devkit-agt": "b" * 40})
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "uv.lock").write_text(
        '[[package]]\nname = "devkit-spec"\nversion = "0.1.0"\n'
        'source = { git = "https://user:secret-token@host/org/devkit-spec?rev=main#'
        + "c" * 40
        + '" }\n\n'
        + lock("b" * 40, "devkit-agt")
    )
    warnings = runtime.revision_warnings(repo)
    assert [item["code"] for item in warnings] == ["RUNTIME_REVISION_MISMATCH"]
    assert "c" * 12 in warnings[0]["detail"] and "a" * 12 in warnings[0]["detail"]
    assert "secret-token" not in warnings[0]["detail"] and "host/" not in warnings[0]["detail"]


def test_revision_parity_is_silent_without_an_exact_signal(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "uv.lock").write_text(lock("c" * 40))
    provision(tmp_path / "older", monkeypatch)  # a runtime provisioned before revisions were recorded
    assert runtime.revision_warnings(repo) == []
    provision(tmp_path / "current", monkeypatch, revisions={"devkit-spec": "c" * 40})
    assert runtime.revision_warnings(repo) == []
    (repo / "uv.lock").write_text(lock("main"))  # a branch, not a revision
    assert runtime.revision_warnings(repo) == []
    (repo / "uv.lock").write_text("not = toml = [[[")
    assert runtime.revision_warnings(repo) == []
    (repo / "uv.lock").write_text("a = " + "[" * 100_000 + "]" * 100_000)  # hostile nesting is no signal either
    assert runtime.revision_warnings(repo) == []
    (repo / "uv.lock").unlink()
    assert runtime.revision_warnings(repo) == []


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


@pytest.mark.parametrize("code", ["RULES_RUN_FAILED", "RECEIPT_STALE", "SELECTION_INVALID", "RULES_LOAD_FAILED"])
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
