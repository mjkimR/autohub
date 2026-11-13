import asyncio
import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import checkout, isolation, runtime, runtime_cache
from app.features.project_management.sdd.decisions import validate_answer
from app.features.project_management.sdd.lock_runtime import Selection

pytestmark = pytest.mark.unit
IDENTITY = "f" * 64


def provision(tmp_path, monkeypatch, **extra) -> Path:
    """A complete cache entry for IDENTITY."""
    monkeypatch.setenv("AUTOHUB_SDD_CACHE", str(tmp_path / "cache"))
    home = runtime_cache.entry(IDENTITY)
    home.mkdir(parents=True)
    (home / ".venv").mkdir()
    pin = {"provider": "devkit-spec", "identity": IDENTITY, "python_prefix": "/usr", "bundles": [], **extra}
    (home / "pin.json").write_text(json.dumps(pin))
    return home


@contextmanager
def resolved(root, home):
    with runtime.runtime_source(root, None) as source:
        source.home = home
        yield source


def selection():
    return Selection(group="dev", export="x", identity=IDENTITY, python="3.13", git=(), registry=())


def receipt(root):
    (root / ".devkit").mkdir()
    (root / ".devkit/installation.json").write_text("{}")


async def test_missing_receipt_never_syncs_or_initializes(tmp_path, monkeypatch):
    invoke = AsyncMock()
    monkeypatch.setattr(checkout, "command", invoke)
    with pytest.raises(ProjectError, match="receipt"):
        await runtime.restore(tmp_path)
    invoke.assert_not_awaited()


async def test_stale_receipt_is_regenerated_best_effort_and_reported(tmp_path, monkeypatch):
    home = provision(tmp_path, monkeypatch, revisions={"devkit-spec": "f" * 40})
    receipt(tmp_path)
    calls = []

    async def invoke(*args, cwd, **kwargs):
        calls.append(args)
        if "--locked" in args:
            raise checkout.SddCommandError("RECEIPT_STALE", "stale")
        return "{}"

    monkeypatch.setattr(checkout, "command", invoke)
    with resolved(tmp_path, home):
        warnings = await runtime.restore(tmp_path)
    assert [item["code"] for item in warnings] == ["RECEIPT_STALE"]
    assert "(devkit-spec ffffffffffff)" in warnings[0]["detail"]
    assert calls == [("devkit", "sync", "--locked", "--format", "json"), ("devkit", "sync", "--format", "json")]


async def test_stale_warning_names_the_locked_revision_when_recorded(tmp_path, monkeypatch):
    home = provision(tmp_path, monkeypatch, revisions={"devkit-spec": "f" * 40})
    with resolved(tmp_path, home):
        assert "(devkit-spec ffffffffffff)" in runtime.stale_warning()["detail"]
    assert runtime.stale_warning()["code"] == "RECEIPT_STALE"  # no runtime detail, still a warning


async def test_failed_regeneration_after_a_stale_receipt_blocks(tmp_path, monkeypatch):
    home = provision(tmp_path, monkeypatch)
    receipt(tmp_path)
    errors = iter([checkout.SddCommandError("RECEIPT_STALE", "stale"), checkout.SddCommandError("SYNC_CONFLICT", "x")])

    async def invoke(*args, cwd, **kwargs):
        raise next(errors)

    monkeypatch.setattr(checkout, "command", invoke)
    with resolved(tmp_path, home), pytest.raises(checkout.SddCommandError) as result:
        await runtime.restore(tmp_path)
    assert result.value.cli_code == "SYNC_CONFLICT"


@pytest.mark.parametrize("code", ["SELECTION_INVALID", "SYNC_CONFLICT", "COMMAND_FAILED"])
async def test_other_sync_failures_still_block(tmp_path, monkeypatch, code):
    home = provision(tmp_path, monkeypatch)
    receipt(tmp_path)
    invoke = AsyncMock(side_effect=checkout.SddCommandError(code, "failed"))
    monkeypatch.setattr(checkout, "command", invoke)
    with resolved(tmp_path, home), pytest.raises(checkout.SddCommandError) as result:
        await runtime.restore(tmp_path)
    assert result.value.cli_code == code
    assert invoke.await_count == 1


async def test_bundles_missing_from_the_locked_runtime_refuse_before_sync(tmp_path, monkeypatch):
    home = provision(tmp_path, monkeypatch, bundles=["spec", "docs"])
    receipt(tmp_path)
    (tmp_path / ".devkit/config.toml").write_text('[presets]\ng-foundation = "all"\n')
    invoke = AsyncMock()
    monkeypatch.setattr(checkout, "command", invoke)
    with resolved(tmp_path, home), pytest.raises(ProjectError, match="g-foundation") as result:
        await runtime.restore(tmp_path)
    assert result.value.code == "SDD_BUNDLES_MISSING"
    invoke.assert_not_awaited()


def test_runtime_pin_must_name_its_own_entry(tmp_path, monkeypatch):
    home = provision(tmp_path, monkeypatch)
    with resolved(tmp_path, home):
        assert runtime.configured_version() == "devkit-lock:" + IDENTITY
        (home / "pin.json").write_text(json.dumps({"provider": "devkit-spec", "identity": "0" * 64}))
        with pytest.raises(ProjectError) as raised:
            runtime.configured_version()
    assert raised.value.code == "SDD_RUNTIME_UNAVAILABLE"


def test_runtime_identity_is_deterministic_and_pathless(tmp_path, monkeypatch):
    home = provision(tmp_path, monkeypatch, python="3.13", revisions={"devkit-spec": "a" * 40})
    with resolved(tmp_path, home):
        assert runtime.runtime_identity() == {
            "provider": "devkit-spec",
            "identity": IDENTITY,
            "python": "3.13",
            "revisions": {"devkit-spec": "a" * 40},
        }


async def test_complete_entry_is_leased_for_the_scope(tmp_path, monkeypatch):
    home = provision(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime, "select", lambda root: selection())
    with runtime.runtime_source(tmp_path, "token"):
        assert await runtime.ensure_runtime() == home
        assert runtime_cache.evict(0) == []  # leased: never evicted mid-evaluation
    assert runtime_cache.evict(0) == [IDENTITY]


async def test_cold_cache_starts_one_install_and_reports_preparing(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOHUB_SDD_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(runtime, "select", lambda root: selection())
    started = asyncio.Event()
    release = asyncio.Event()
    builds = []

    async def build(chosen, token):
        builds.append(token)
        started.set()
        await release.wait()
        return True

    monkeypatch.setattr("app.features.project_management.sdd.runtime_install.build", build)
    runtime._installs.clear()

    async def caller():
        with runtime.runtime_source(tmp_path, "token"), pytest.raises(ProjectError) as raised:
            await runtime.ensure_runtime()
        return raised.value

    errors = await asyncio.gather(*(caller() for _ in range(5)))
    await started.wait()
    assert builds == ["token"]
    assert all(error.status == 503 and error.code == "SDD_RUNTIME_PREPARING" for error in errors)
    release.set()
    task = runtime.install_task(IDENTITY)
    assert task is not None
    await task


async def test_caller_deadline_does_not_cancel_the_install(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOHUB_SDD_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(runtime, "select", lambda root: selection())
    finished = asyncio.Event()

    async def build(chosen, token):
        await asyncio.sleep(0.2)
        finished.set()
        return True

    monkeypatch.setattr("app.features.project_management.sdd.runtime_install.build", build)
    runtime._installs.clear()

    async def slow_request():
        with runtime.runtime_source(tmp_path, "token"):
            try:
                await runtime.ensure_runtime()
            except ProjectError:
                await asyncio.sleep(10)  # the request keeps waiting until its deadline

    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.05):
            await slow_request()
    await asyncio.wait_for(finished.wait(), 2)
    task = runtime.install_task(IDENTITY)
    assert task is not None
    await asyncio.wait_for(task, 2)
    assert not task.cancelled()


async def test_recorded_failure_is_reported_without_reinstalling(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOHUB_SDD_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(runtime, "select", lambda root: selection())
    runtime_cache.record_failure(IDENTITY, "SDD_RUNTIME_SOURCE_UNAVAILABLE", runtime_cache.token_scope("token"))
    monkeypatch.setattr(runtime, "_start_install", lambda *args: pytest.fail("reinstalled during the retry delay"))
    with runtime.runtime_source(tmp_path, "token"), pytest.raises(ProjectError) as raised:
        await runtime.ensure_runtime()
    assert raised.value.status == 422 and raised.value.code == "SDD_RUNTIME_SOURCE_UNAVAILABLE"
    assert "token" not in raised.value.detail and "github.com" not in raised.value.detail


async def test_git_safe_never_resolves_a_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "ensure_runtime", AsyncMock(side_effect=AssertionError("resolved a runtime")))
    monkeypatch.setattr(isolation, "isolated_git", lambda root, args: ["sandbox", "git", *args])

    async def invoke(*args, **kwargs):
        return "ok"

    monkeypatch.setattr(checkout, "_command", invoke)
    with runtime.runtime_source(tmp_path, "token"):
        assert await checkout.command("git-safe", "status", cwd=tmp_path) == "ok"


async def test_cli_drops_credentials_and_requires_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "private-token")
    monkeypatch.setenv("DATABASE_URL", "private-db")
    monkeypatch.setattr(runtime, "ensure_runtime", AsyncMock(return_value=Path("/cache/x")))
    monkeypatch.setattr(runtime, "runtime_pin", lambda: {"python_prefix": "/usr"})
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


@pytest.mark.parametrize("platform,runner", [("darwin", "/usr/bin/sandbox-exec"), ("linux", "/usr/bin/bwrap")])
def test_isolated_cli_uses_the_distribution_entrypoint(tmp_path, monkeypatch, platform, runner):
    monkeypatch.setattr(isolation.sys, "platform", platform)
    monkeypatch.setattr(isolation.shutil, "which", lambda _: runner)
    command = isolation.isolated_command(tmp_path, tmp_path, ("--version",), "/usr")
    assert command[-6:] == [str(tmp_path / ".venv/bin/python"), "-I", "-B", "-m", "devkit_dist", "--version"]


@pytest.mark.parametrize(
    "code",
    [
        "RULES_RUN_FAILED",
        "RECEIPT_STALE",
        "SELECTION_INVALID",
        "RULES_LOAD_FAILED",
        "SPEC_PROPOSAL_ACCEPT_REFUSED",
        "SPEC_PROPOSAL_GATE_NOT_OPEN",
        "SPEC_PROPOSAL_WRONG_WORKTREE",
        "SPEC_PROPOSAL_POLICY_NOT_AUTO",
        "SPEC_LIFECYCLE_INACTIVE",
        "DEVELOPMENT_CONFIG_INVALID",
        "SPEC_CONFIG_INVALID",
    ],
)
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
    assert checkout.CLI_FIXES[code] in result.value.detail


@pytest.mark.parametrize(
    ("code", "hint"),
    [
        ("SPEC_LIFECYCLE_INACTIVE", 'approach = "sdd"'),
        ("DEVELOPMENT_CONFIG_INVALID", '"sdd" or "adaptive-dev"'),
        ("SPEC_CONFIG_INVALID", "[tool.spec]"),
        ("SPEC_PROPOSAL_POLICY_NOT_AUTO", 'plan-accept = "auto"'),
    ],
)
def test_configuration_refusals_name_the_setting_to_change(code, hint):
    assert hint in checkout.CLI_FIXES[code]


@pytest.mark.parametrize("legacy", [False, True])
def test_operator_answer_publication_preserves_the_decider_and_legacy_records(legacy):
    from app.features.project_management.sdd.decisions import answer_envelope_record, publication_instructions

    operation = {"id": "d1", "actor": "user:fixture", "value": "a", "note": "Keep TOML"}
    record = answer_envelope_record(operation, {"id": "question:worker-01.q1"})
    assert record["by"] == "user" and record["operation"]["actor"] == "user:fixture"
    if legacy:
        record.pop("by")
    payload = json.loads(publication_instructions({"decision_records": [record]}).splitlines()[-1])
    assert payload == [
        {
            "answers_to": "worker-01.yaml",
            "answers": [{"question": "q1", "choice": "a", "decision": "Keep TOML", "by": "user"}],
        }
    ]


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
    evidence["current"]["requests"] = [{"id": "gate:dev-integration", "kind": "approve", "answer": "given"}]
    with pytest.raises(ProjectError, match="integration approval"):
        validate_answer(evidence, {"request": "gate:dev-integration", "action": "accept"})
    options = [{"id": "a", "description": "", "eligible": True, "recommended": True}]
    question = {"id": "question:worker-01.q1", "kind": "choose", "answer": "envelope", "options": options}
    evidence["current"]["requests"] = [question]
    assert validate_answer(evidence, {"request": "question:worker-01.q1", "action": "accept", "value": "a"})
    assert validate_answer(evidence, {"request": "question:worker-01.q1", "action": "accept", "note": "Outside"})
    with pytest.raises(ProjectError, match="never declined"):
        validate_answer(evidence, {"request": "question:worker-01.q1", "action": "decline"})
    with pytest.raises(ProjectError, match="one of the question's options"):
        validate_answer(evidence, {"request": "question:worker-01.q1", "action": "accept", "value": "zzz"})
    with pytest.raises(ProjectError, match="Write the decision"):
        validate_answer(evidence, {"request": "question:worker-01.q1", "action": "accept", "note": "  "})


async def test_symlinked_entry_venv_is_refused(tmp_path, monkeypatch):
    home = provision(tmp_path, monkeypatch)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (home / ".venv").rmdir()
    (home / ".venv").symlink_to(elsewhere)
    monkeypatch.setattr(runtime, "select", lambda root: selection())
    with runtime.runtime_source(tmp_path, "token"), pytest.raises(ProjectError) as raised:
        await runtime.ensure_runtime()
    assert raised.value.code == "SDD_RUNTIME_INSTALL_FAILED"


async def test_devkit_sandbox_reads_the_hub_prefix_not_the_recorded_one(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(runtime, "ensure_runtime", AsyncMock(return_value=tmp_path))
    monkeypatch.setattr(runtime, "runtime_pin", lambda: {"python_prefix": "/"})
    monkeypatch.setattr(
        isolation, "isolated_command", lambda home, root, args, prefix: seen.append(prefix) or ["sandbox"]
    )
    monkeypatch.setattr(checkout, "_command", AsyncMock(return_value="ok"))
    await checkout.command("devkit", "--version", cwd=tmp_path)
    from app.features.project_management.sdd.lock_runtime import interpreter_prefix

    assert seen == [interpreter_prefix()] and seen[0] != "/"
