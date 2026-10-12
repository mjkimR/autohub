import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.specrig import checkout, runtime, services

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "source,version",
    [
        ({"kind": "local"}, "0.1.2"),
        ({"kind": "release", "repository": "other/repo"}, "0.1.2"),
        ({"kind": "release", "repository": "mjkimR/specrig"}, "9.0.0"),
    ],
)
async def test_layered_receipt_mismatch_never_restores_or_initializes(tmp_path, monkeypatch, source, version):
    harness = tmp_path / ".specrig"
    harness.mkdir()
    (harness / "installation.json").write_text(
        json.dumps({"layout": "layered", "version": version, "commit": "abc", "source": source})
    )
    invoke = AsyncMock()
    monkeypatch.setattr(runtime, "command", invoke)
    with pytest.raises(ProjectError, match="pinned release"):
        await runtime.restore(tmp_path, "specrig version 0.1.2 commit=abc")
    invoke.assert_not_awaited()


async def test_cli_drops_credentials_go_and_repository_runner_cache(tmp_path, monkeypatch):
    cache = tmp_path / ".specrig/.cache"
    cache.mkdir(parents=True)
    (cache / "rules-runner").write_text("untrusted")
    monkeypatch.setenv("GH_TOKEN", "private-token")
    monkeypatch.setenv("DATABASE_URL", "private-db")
    monkeypatch.setattr(checkout.shutil, "which", lambda name: "/usr/bin/true")

    async def invoke(*args, **kwargs):
        env = kwargs["env"]
        assert set(env) == {"PATH", "TMPDIR", "LANG"}
        assert sorted(p.name for p in Path(env["PATH"]).iterdir()) == ["git", "specrig"]
        assert Path(env["TMPDIR"]) == Path(env["TMPDIR"]).resolve()
        assert not cache.exists()
        return "safe"

    monkeypatch.setattr(checkout, "_command", invoke)
    assert await checkout.command("specrig", "lint", cwd=tmp_path) == "safe"


@pytest.mark.parametrize("code", ["RULE_VIOLATIONS_DETECTED", "CUSTOM_RULES_REQUIRE_GO", "UNEXPECTED_ERROR"])
async def test_diagnostics_preserve_known_code_without_leaking_stderr(tmp_path, monkeypatch, code):
    process = AsyncMock()
    process.returncode = 1
    process.communicate.return_value = (
        b"[RULE-example] invalid",
        f"[ERROR]  ({code}) secret-token private-path".encode(),
    )
    monkeypatch.setattr(checkout.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    with pytest.raises(checkout.SpecrigCommandError) as result:
        await checkout._command("specrig", "lint", cwd=tmp_path, env={}, allow_failure=False)
    assert result.value.cli_code == code
    assert "secret-token" not in result.value.detail
    assert "private-path" not in result.value.detail


@pytest.mark.parametrize("code", ["RULE_VIOLATIONS_DETECTED", "CUSTOM_RULES_REQUIRE_GO", "UNEXPECTED_ERROR"])
async def test_only_rule_violations_return_repairable_evidence(tmp_path, monkeypatch, code):
    (tmp_path / ".specrig").mkdir()
    (tmp_path / "spec").mkdir()
    (tmp_path / "spec/spec.md").touch()
    monkeypatch.setattr(services, "configured_version", lambda: "fixture")
    monkeypatch.setattr(services, "restore", AsyncMock())

    async def invoke(*args, **kwargs):
        if args[1] == "lint":
            raise checkout.SpecrigCommandError(code, "safe diagnostic")
        return "fixture" if args[1] == "--version" else "base"

    monkeypatch.setattr(services, "command", invoke)
    monkeypatch.setattr(
        services,
        "cli",
        AsyncMock(
            side_effect=[
                {"schema_version": 1, "keys": {}},
                {"id": "workflow", "hash": "hash"},
                [],
                {"bound": True, "stage": {"exit": ["lint-ci-clean"]}},
                {"envelopes": []},
            ]
        ),
    )
    if code == "RULE_VIOLATIONS_DETECTED":
        result = await services.SpecrigService().evaluate(tmp_path, "spec", "head", "base", None, True)
        assert result["lint_diagnostic"] == "safe diagnostic"
        assert not result["integrated"]
    else:
        with pytest.raises(checkout.SpecrigCommandError):
            await services.SpecrigService().evaluate(tmp_path, "spec", "head", "base", None, True)
