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
    calls = []
    failures = {}
    probe = {"output": {"python_prefix": "/", "packages": {"devkit-spec": "0.1.6"}, "bundles": ["spec", "docs"]}}
    monkeypatch.setattr(
        runtime_install, "isolated_build", lambda writable, py, uv, args: ["SANDBOX", str(writable), *args]
    )
    hooks = {}
    paths = {"probe": [], "install": []}

    def isolated_python(writable, py, prefix, code):
        paths["probe"].append(Path(writable))
        return ["SANDBOX-PY", code]

    def sandboxed(writable, readable, invocation):
        paths["install"].append((Path(writable), [Path(item) for item in readable]))
        return ["SANDBOX", str(writable), *invocation]

    monkeypatch.setattr(runtime_install, "isolated_python", isolated_python)
    monkeypatch.setattr(runtime_install, "sandboxed", sandboxed)

    async def run(args, *, cwd, env, timeout, code, group=False):
        calls.append({"args": [str(a) for a in args], "env": env, "code": code, "cwd": cwd})
        step = args[5] if args[0] == "git" else args[0]  # git -c ... -c ... <step>
        if failures.get(step) == code:
            raise runtime_install.InstallFailure(code)
        if len(args) > 1 and args[1] == "venv":
            Path(args[-1]).mkdir(parents=True)
        if "checkout" in args:
            for sub in ("packages/devkit-spec", "packages/devkit-dist"):
                (Path(cwd) / sub).mkdir(parents=True, exist_ok=True)
                (Path(cwd) / sub / "pyproject.toml").write_text("[project]\n")
        if args[0] == "SANDBOX" and "--out-dir" in args:
            out = Path(args[args.index("--out-dir") + 1])
            out.mkdir(exist_ok=True)
            (out / f"{Path(args[-1]).name}-1.0-py3-none-any.whl").write_text("")
        if args[0] == "SANDBOX-PY":
            if hook := hooks.get("probe"):
                hook(cwd)
            return json.dumps(probe["output"])
        return ""

    monkeypatch.setattr(runtime_install, "run", run)
    probe["hooks"] = hooks
    probe["paths"] = paths
    return calls, failures, probe


async def test_install_publishes_a_complete_entry_with_an_identity_pin(fake, selection):
    assert await runtime_install.build(selection, TOKEN) is True
    pin = json.loads((runtime_cache.entry(IDENTITY) / "pin.json").read_text())
    assert pin["identity"] == IDENTITY and pin["bundles"] == ["spec", "docs"]
    assert pin["revisions"] == {"devkit-dist": REVISION, "devkit-spec": REVISION}
    assert not list(runtime_cache.cache_root().glob(".staging-*"))
    assert not (runtime_cache.entry(IDENTITY) / "src").exists()


async def test_token_is_used_only_by_hub_process_fetches(fake, selection):
    calls, _, _ = fake
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
    calls, _, _ = fake
    await runtime_install.build(selection, TOKEN)
    builds = [call for call in calls if call["args"][0] == "SANDBOX" and "build" in call["args"]]
    assert len(builds) == 2
    assert all({"--offline", "--no-build-isolation", "--wheel"} <= set(call["args"]) for call in builds)
    assert all(call["env"].get("UV_OFFLINE") == "1" for call in builds)
    registry = next(call for call in calls if "--require-hashes" in call["args"])
    assert {"--only-binary", ":all:", "--no-deps"} <= set(registry["args"])


async def test_unreadable_source_records_a_failure_without_an_entry(fake, selection):
    _, failures, _ = fake
    failures["fetch"] = "SDD_RUNTIME_SOURCE_UNAVAILABLE"
    assert await runtime_install.build(selection, TOKEN) is True
    assert runtime_cache.failure(IDENTITY, runtime_cache.token_scope(TOKEN)) == "SDD_RUNTIME_SOURCE_UNAVAILABLE"
    assert not runtime_cache.complete(IDENTITY)
    assert not list(runtime_cache.cache_root().glob(".staging-*"))


async def test_a_held_claim_skips_the_install(fake, selection):
    calls, _, _ = fake
    claim = runtime_cache.try_build_lock(IDENTITY)
    assert claim is not None
    try:
        assert await runtime_install.build(selection, TOKEN) is False
    finally:
        claim.release()
    assert calls == []


def test_linux_sandbox_unshares_network_and_binds_one_writable_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(isolation.sys, "platform", "linux")
    monkeypatch.setattr(isolation.shutil, "which", lambda name: "/usr/bin/bwrap" if name == "bwrap" else None)
    command = isolation.isolated_build(
        tmp_path, Path("/opt/sdd-build/.venv/bin/python"), Path("/usr/bin/uv"), ("build",)
    )
    assert "--unshare-all" in command and command.count("--bind") == 1
    assert command[command.index("--bind") + 1] == str(tmp_path)


async def test_builds_write_only_work_and_the_wheel_install_runs_sandboxed(fake, selection):
    calls, _, _ = fake
    await runtime_install.build(selection, TOKEN)
    sandboxed = [call for call in calls if call["args"][0] == "SANDBOX"]
    builds = [call for call in sandboxed if "build" in call["args"]]
    installs = [call for call in sandboxed if "pip" in call["args"]]
    assert all(Path(call["args"][1]).name == runtime_install.WORK for call in builds)
    assert len(installs) == 1 and Path(installs[0]["args"][1]).name == ".venv"  # the wheel install writes only the venv
    hub_uv = [call for call in calls if call["args"][0] not in ("SANDBOX", "SANDBOX-PY", "git")]
    # After registry wheels are installed, the Hub process never runs uv against the venv again.
    assert [call["args"][1:3] for call in hub_uv] == [["venv", "-q"], ["pip", "install"]]


async def test_pin_prefix_comes_from_the_hub_not_the_probe(fake, selection):
    await runtime_install.build(selection, TOKEN)
    pin = json.loads((runtime_cache.entry(IDENTITY) / "pin.json").read_text())
    assert pin["python_prefix"] != "/"  # the probe claimed "/"
    assert Path(pin["python_prefix"]).is_absolute()


@pytest.mark.parametrize(
    "output",
    [["not", "an", "object"], {"packages": {"devkit-spec": 1}, "bundles": []}, {"packages": {}, "bundles": []}],
)
async def test_malformed_inventory_records_a_failure(fake, selection, output):
    _, _, probe = fake
    probe["output"] = output
    assert await runtime_install.build(selection, TOKEN) is True
    assert runtime_cache.failure(IDENTITY, runtime_cache.token_scope(TOKEN)) == "SDD_RUNTIME_INSTALL_FAILED"
    assert not runtime_cache.complete(IDENTITY)


async def test_unexpected_errors_still_back_off(fake, selection, monkeypatch):
    async def broken(*args):
        raise OSError("disk full at /secret/path")

    monkeypatch.setattr(runtime_install, "write_pin", broken)
    assert await runtime_install.build(selection, TOKEN) is True
    assert runtime_cache.failure(IDENTITY, runtime_cache.token_scope(TOKEN)) == "SDD_RUNTIME_INSTALL_FAILED"


def test_symlinked_build_output_is_refused(tmp_path):
    wheels = tmp_path / runtime_install.WORK / "wheels"
    wheels.mkdir(parents=True)
    target = tmp_path / "outside.whl"
    target.write_text("")
    (wheels / "a-1.0-py3-none-any.whl").symlink_to(target)
    with pytest.raises(runtime_install.InstallFailure):
        runtime_install.built_wheels(tmp_path, 1)


async def test_a_swapped_venv_after_the_probe_fails_the_install(fake, selection, tmp_path):
    _, _, probe = fake
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    def swap(venv):
        import shutil

        shutil.rmtree(venv)
        Path(venv).symlink_to(elsewhere)

    probe["hooks"]["probe"] = swap
    assert await runtime_install.build(selection, TOKEN) is True
    assert runtime_cache.failure(IDENTITY, runtime_cache.token_scope(TOKEN)) == "SDD_RUNTIME_INSTALL_FAILED"
    assert not runtime_cache.complete(IDENTITY) and not list(elsewhere.iterdir())


async def test_later_sandboxes_cannot_write_the_staging_root(fake, selection):
    calls, _, _ = fake
    await runtime_install.build(selection, TOKEN)
    writable = [Path(call["args"][1]).name for call in calls if call["args"][0] == "SANDBOX"]
    assert set(writable) == {runtime_install.WORK, ".venv"}


async def test_probe_and_install_write_only_the_venv_and_read_the_hub_prefix(fake, selection):
    from app.features.project_management.sdd.lock_runtime import interpreter_prefix

    _, _, probe = fake
    await runtime_install.build(selection, TOKEN)
    assert [path.name for path in probe["paths"]["probe"]] == [".venv"]
    ((writable, readable),) = probe["paths"]["install"]
    assert writable.name == ".venv" and Path(interpreter_prefix()) in readable


async def test_hub_never_acts_below_the_venv_after_a_late_swap(fake, selection, tmp_path, monkeypatch):
    """A lingering macOS sandbox process swapping .venv after the last check steers no Hub file action."""
    import shutil

    outside = tmp_path / "outside"
    (outside / ".tmp").mkdir(parents=True)
    original = runtime_install._clean

    def swap_then_clean(staged):
        shutil.rmtree(staged / ".venv")
        (staged / ".venv").symlink_to(outside)
        original(staged)

    monkeypatch.setattr(runtime_install, "_clean", swap_then_clean)
    await runtime_install.build(selection, TOKEN)
    assert (outside / ".tmp").is_dir()  # untouched by the Hub
