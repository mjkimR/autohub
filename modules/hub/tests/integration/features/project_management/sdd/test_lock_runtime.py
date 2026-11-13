"""Real isolated evaluation with the runtime the fixture repository's own uv.lock selects."""

import subprocess
from pathlib import Path

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import checkout as checkout_module
from app.features.project_management.sdd import runtime, runtime_cache, runtime_install
from app.features.project_management.sdd.services import SddService

from tests.integration.features.project_management.sdd import test_cli
from tests.integration.features.project_management.sdd.test_cli import SPEC, commit, run

pytestmark = pytest.mark.integration
checkout = test_cli.checkout


async def test_evaluation_uses_the_locked_runtime_and_records_its_identity(checkout):
    root, head = checkout
    evidence = await SddService().evaluate(root, SPEC, head, head, None, False)
    home = runtime.current_source().home
    assert home is not None
    assert evidence["snapshot"]["cli_version"] == f"devkit-lock:{home.name}"
    assert home == runtime_cache.entry(home.name)


async def test_changed_runtime_identity_continues_an_admitted_run(checkout):
    root, head = checkout
    service = SddService()
    admitted = (await service.evaluate(root, SPEC, head, head, None, False))["snapshot"]
    earlier = {**admitted, "cli_version": "devkit-lock:" + "0" * 64}
    evidence = await service.evaluate(root, SPEC, head, head, earlier, False)
    assert evidence["snapshot"]["cli_version"] == admitted["cli_version"]


async def test_bundle_without_a_locked_package_is_refused_before_sync(checkout):
    root, _ = checkout
    config = root / ".devkit/config.toml"
    config.write_text(config.read_text() + '\n[presets]\napp-common = "all"\n')
    with pytest.raises(ProjectError, match="app-common") as raised:
        await runtime.restore(root)
    assert raised.value.code == "SDD_BUNDLES_MISSING"


async def test_repository_without_a_devkit_lock_is_refused_through_checkout(checkout, monkeypatch, tmp_path):
    root, _ = checkout
    (root / "uv.lock").unlink()
    head = commit(root, "Drop the lock")
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "--bare", "--quiet", str(root), str(bare)], check=True)
    monkeypatch.setattr(checkout_module, "remote_url", lambda repository: str(bare))
    with pytest.raises(ProjectError) as raised:
        await SddService().inspect("team/app", SPEC, {"head": {"sha": head}, "base": {"sha": head}}, "token")
    assert raised.value.status == 422 and raised.value.code == "SDD_RUNTIME_UNLOCKED"


async def test_activity_branch_git_needs_no_runtime(checkout, monkeypatch):
    root, head = checkout
    monkeypatch.setattr(runtime, "ensure_runtime", pytest.fail)
    assert (await checkout_module.command("git-safe", "rev-parse", "HEAD", cwd=root)).strip() == head


HOOK = """
import os, socket
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=2).close()
            network = "open"
        except OSError:
            network = "blocked"
        planted = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(self.root))), ".venv", "planted.pth")
        try:
            with open(planted, "w") as handle:
                handle.write("import os; os.system('touch /tmp/escaped')")
            venv = "written"
        except OSError:
            venv = "denied"
        observed = {"network": network, "secret": os.environ.get("SDD_TEST_SECRET"), "venv": venv}
        with open(os.path.join(self.root, "observed.txt"), "w") as handle:
            handle.write(repr(observed))
"""


async def test_source_build_hook_cannot_reach_the_network_or_credentials(tmp_path, monkeypatch):
    build = Path(runtime_install.build_home())
    if not (build / ".venv/bin/python").exists():
        pytest.skip("requires the pinned build environment (just install-sdd .cache/sdd-build config/sdd-build)")
    monkeypatch.setenv("SDD_TEST_SECRET", "host-secret")
    staged = tmp_path / "staged"
    source = staged / runtime_install.WORK / "src/probe"
    source.mkdir(parents=True)
    (source / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
        '[project]\nname = "probe"\nversion = "1.0"\n\n'
        "[tool.hatch.build.targets.wheel]\nbypass-selection = true\n\n"
        '[tool.hatch.build.hooks.custom]\npath = "hatch_build.py"\n'
    )
    (source / "hatch_build.py").write_text(HOOK)
    venv = staged / ".venv"
    run(staged, runtime_install.uv_binary(), "venv", "-q", "--python", str(runtime_install.interpreter()), str(venv))
    (venv / ".tmp").mkdir()
    await runtime_install.build_sources({"probe": source}, staged, venv, runtime_install._identity(venv))
    observed = (source / "observed.txt").read_text()
    assert "'network': 'blocked'" in observed and "host-secret" not in observed
    assert "'venv': 'denied'" in observed and not (venv / "planted.pth").exists()
    assert list((staged / runtime_install.WORK / "wheels").glob("probe-1.0-*.whl"))
    assert list(venv.glob("lib/python*/site-packages/probe-1.0.dist-info"))  # installed by the sandboxed step
