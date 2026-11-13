"""The install pipeline keeps the connector token in Hub-process fetches and builds sources in the sandbox."""

import json
from pathlib import Path

import pytest
from app.features.project_management.sdd import isolation, runtime_cache, runtime_install
from app.features.project_management.sdd.lock_runtime import GitSource, Selection

TOKEN = "ghs_secret_connector_token"
IDENTITY = "e" * 64
REVISION = "a1ffedafd49ccd4bb6298bacacca1c25c0cf48ef"


@pytest.fixture
def selection():
    return Selection(
        group="dev",
        export="...",
        identity=IDENTITY,
        python="3.13",
        git=(
            GitSource("devkit-spec", "mjkimR/devkit", REVISION, "packages/devkit-spec"),
            GitSource("devkit-dist", "mjkimR/devkit", REVISION, "packages/devkit-dist"),
        ),
        registry=("click==8.5.1 --hash=sha256:" + "b" * 64,),
    )


@pytest.fixture
def fake(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOHUB_SDD_CACHE", str(tmp_path / "cache"))
    build = tmp_path / "build/.venv/bin"
    build.mkdir(parents=True)
    (build / "python").write_text("")
    monkeypatch.setenv("AUTOHUB_SDD_BUILD", str(tmp_path / "build"))
    monkeypatch.setattr(runtime_install, "isolated_build", lambda staging, py, uv, args: ["SANDBOX", *args])
    monkeypatch.setattr(runtime_install, "isolated_python", lambda writable, py, prefix, code: ["SANDBOX-PY", code])
    calls = []
    failures = {}

    async def run(args, *, cwd, env, timeout, code, group=False):
        calls.append({"args": [str(a) for a in args], "env": env, "code": code, "cwd": cwd})
        step = args[5] if args[0] == "git" else args[0]  # git -c ... -c ... <step>
        if failures.get(step) == code:
            raise runtime_install.InstallFailure(code)
        if "checkout" in args:
            for sub in ("packages/devkit-spec", "packages/devkit-dist"):
                (Path(cwd) / sub).mkdir(parents=True, exist_ok=True)
                (Path(cwd) / sub / "pyproject.toml").write_text("[project]\n")
        if args[0] == "SANDBOX":
            out = Path(args[args.index("--out-dir") + 1])
            out.mkdir(exist_ok=True)
            (out / f"{Path(args[-1]).name}-1.0-py3-none-any.whl").write_text("")
        if args[0] == "SANDBOX-PY":
            return json.dumps(
                {"python_prefix": "/usr/local", "packages": {"devkit-spec": "0.1.6"}, "bundles": ["spec", "docs"]}
            )
        return ""

    monkeypatch.setattr(runtime_install, "run", run)
    return calls, failures


async def test_install_publishes_a_complete_entry_with_an_identity_pin(fake, selection):
    assert await runtime_install.build(selection, TOKEN) is True
    pin = json.loads((runtime_cache.entry(IDENTITY) / "pin.json").read_text())
    assert pin["identity"] == IDENTITY and pin["bundles"] == ["spec", "docs"]
    assert pin["revisions"] == {"devkit-dist": REVISION, "devkit-spec": REVISION}
    assert not list(runtime_cache.cache_root().glob(".staging-*"))
    assert not (runtime_cache.entry(IDENTITY) / "src").exists()


async def test_token_is_used_only_by_hub_process_fetches(fake, selection):
    calls, _ = fake
    await runtime_install.build(selection, TOKEN)
    fetches = [call for call in calls if call["args"][0] == "git"]
    others = [call for call in calls if call["args"][0] != "git"]
    assert fetches and all("GIT_CONFIG_VALUE_0" in call["env"] for call in fetches)
    assert sum("fetch" in call["args"] for call in fetches) == 1  # one fetch per repository revision
    for call in others:
        assert not any(TOKEN in value for value in call["env"].values())
        assert not any(TOKEN in arg for arg in call["args"])
        assert set(call["env"]) <= {"PATH", "HOME", "TMPDIR", "LANG", "UV_NO_CONFIG", "UV_PYTHON_DOWNLOADS"} | {
            "UV_CACHE_DIR",
            "NO_COLOR",
            "UV_OFFLINE",
        }
    assert TOKEN not in (runtime_cache.entry(IDENTITY) / "pin.json").read_text()


async def test_sources_build_in_the_sandbox_offline_and_wheels_install_hashed(fake, selection):
    calls, _ = fake
    await runtime_install.build(selection, TOKEN)
    builds = [call for call in calls if call["args"][0] == "SANDBOX"]
    assert len(builds) == 2
    assert all({"--offline", "--no-build-isolation", "--wheel"} <= set(call["args"]) for call in builds)
    assert all(call["env"].get("UV_OFFLINE") == "1" for call in builds)
    registry = next(call for call in calls if "--require-hashes" in call["args"])
    assert {"--only-binary", ":all:", "--no-deps"} <= set(registry["args"])


async def test_unreadable_source_records_a_failure_without_an_entry(fake, selection):
    _, failures = fake
    failures["fetch"] = "SDD_RUNTIME_SOURCE_UNAVAILABLE"
    assert await runtime_install.build(selection, TOKEN) is True
    assert runtime_cache.failure(IDENTITY) == "SDD_RUNTIME_SOURCE_UNAVAILABLE"
    assert not runtime_cache.complete(IDENTITY)
    assert not list(runtime_cache.cache_root().glob(".staging-*"))


async def test_a_held_claim_skips_the_install(fake, selection):
    calls, _ = fake
    claim = runtime_cache.try_build_lock(IDENTITY)
    try:
        assert await runtime_install.build(selection, TOKEN) is False
    finally:
        claim.release()
    assert calls == []


def test_linux_sandbox_unshares_network_and_binds_one_writable_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(isolation.sys, "platform", "linux")
    monkeypatch.setattr(isolation.shutil, "which", lambda name: "/usr/bin/bwrap" if name == "bwrap" else None)
    command = isolation.isolated_build(tmp_path, Path("/opt/sdd-build/.venv/bin/python"), Path("/usr/bin/uv"), ("build",))
    assert "--unshare-all" in command and command.count("--bind") == 1
    assert command[command.index("--bind") + 1] == str(tmp_path)
