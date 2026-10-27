"""Real isolated bundle restore through the repository's assigned runtime."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import checkout as checkout_module
from app.features.project_management.sdd.profiles import runtime_scope
from app.features.project_management.sdd.runtime import restore, runtime_pin
from app.features.project_management.sdd.services import SddService

from tests.integration.features.project_management.sdd import test_cli
from tests.integration.features.project_management.sdd.test_cli import SPEC, commit, run

pytestmark = pytest.mark.integration
checkout = test_cli.checkout


async def test_app_common_project_requires_its_profile_and_keeps_the_execution_pin(checkout, monkeypatch, tmp_path):
    root, _ = checkout
    profile = os.environ.get("AUTOHUB_TEST_SDD_APP_COMMON")
    if not profile:
        if os.environ.get("AUTOHUB_REQUIRE_SDD"):
            pytest.fail("Install the app-common profile and set AUTOHUB_TEST_SDD_APP_COMMON")
        pytest.skip("requires app-common runtime")
    home = Path(profile).resolve()
    monkeypatch.setenv(
        "AUTOHUB_SDD_PROFILES",
        json.dumps(
            {
                "profiles": {"app-common": str(home)},
                "repositories": {"team/app": "app-common"},
            }
        ),
    )
    config = root / ".devkit/config.toml"
    config.write_text(config.read_text() + '\n[presets]\napp-common = "all"\n')
    with runtime_scope("team/plain"), pytest.raises(ProjectError, match="missing bundles: app-common"):
        await restore(root)
    run(root, str(home / ".venv/bin/devkit"), "sync")
    head = commit(root, "Select reviewed app-common bundle")
    with runtime_scope("team/app"):
        assert "app-common" in runtime_pin()["bundles"]
        service = SddService()
        evidence = await service.evaluate(root, SPEC, head, head, None, False)
        assert evidence["current"]["bound"]
        assert evidence["warnings"] == []
        status = await service.runtime_status()
        assert status["ok"] and status["profile"] == "app-common"
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "--bare", "--quiet", str(root), str(bare)], check=True)
    monkeypatch.setattr(checkout_module, "remote_url", lambda repository: str(bare))
    inspected = await service.inspect("team/app", SPEC, {"head": {"sha": head}, "base": {"sha": head}}, "token")
    assert inspected["snapshot"] == evidence["snapshot"]
    # Reassigning a repository cannot silently change a live run's rules/runtime.
    with runtime_scope("team/plain"), pytest.raises(ProjectError, match="version"):
        await service.evaluate(root, SPEC, head, head, evidence["snapshot"], False)
