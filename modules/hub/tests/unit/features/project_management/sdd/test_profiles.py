"""Runtime selection cannot leak across concurrent repository evaluations."""

import asyncio
import json
from pathlib import Path

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import profiles, runtime

pytestmark = pytest.mark.unit


def mapping(monkeypatch):
    monkeypatch.setenv("AUTOHUB_SDD_HOME", "/opt/base")
    monkeypatch.setenv(
        "AUTOHUB_SDD_PROFILES",
        json.dumps(
            {
                "profiles": {"app-common": "/opt/app-common"},
                "repositories": {"team/with-app": "app-common"},
            }
        ),
    )


async def test_repository_profiles_are_task_local_and_reset_after_failure(monkeypatch):
    mapping(monkeypatch)
    entered = asyncio.Event()
    observed = asyncio.Event()

    async def custom():
        with pytest.raises(RuntimeError), profiles.runtime_scope("Team/With-App"):
            entered.set()
            await observed.wait()
            assert runtime.runtime_home() == Path("/opt/app-common")
            raise RuntimeError("evaluation stopped")
        assert runtime.runtime_home() == Path("/opt/base")

    async def default():
        await entered.wait()
        with profiles.runtime_scope("team/plain"):
            assert runtime.runtime_home() == Path("/opt/base")
            observed.set()

    await asyncio.gather(custom(), default())
    assert profiles.current()[0] == "default"


@pytest.mark.parametrize(
    "config",
    [
        [],
        {"repository": {"team/repo": "default"}},
        {"profiles": []},
        {"profiles": {"app": "relative"}},
        {"profiles": {"default": "/opt/other"}},
        {"repositories": {"team/repo": "absent"}},
    ],
)
def test_invalid_server_mapping_never_falls_back(monkeypatch, config):
    monkeypatch.setenv("AUTOHUB_SDD_PROFILES", json.dumps(config))
    with pytest.raises(ProjectError) as error:
        profiles.selection("team/repo")
    assert error.value.code == "SDD_PROFILE_INVALID"


def test_bundle_preflight_uses_selection_and_receipt_without_running_project_code(tmp_path, monkeypatch):
    mapping(monkeypatch)
    (tmp_path / ".devkit").mkdir()
    (tmp_path / ".devkit/config.toml").write_text('[presets]\napp-common = "all"\nunused = false\n')
    (tmp_path / ".devkit/installation.json").write_text(json.dumps({"assets": [{"bundle": "spec"}]}))
    monkeypatch.setattr(runtime, "runtime_pin", lambda: {"bundles": ["spec", "devkit"]})
    with (
        profiles.runtime_scope("team/plain"),
        pytest.raises(ProjectError, match="missing bundles: app-common") as error,
    ):
        runtime.check_bundles(tmp_path)
    assert error.value.code == "SDD_BUNDLES_MISSING"
    monkeypatch.setattr(runtime, "runtime_pin", lambda: {"bundles": ["spec", "devkit", "app-common"]})
    with profiles.runtime_scope("team/with-app"):
        runtime.check_bundles(tmp_path)


def test_workflow_pin_is_stable_across_checkouts_but_covers_effective_semantics():
    from app.features.project_management.sdd.contracts import workflow_hash

    definition = {
        "id": "workflow",
        "stages": [{"id": "review", "exit": ["checked"]}],
        "approvals": {"integration": "ask"},
    }
    expected = workflow_hash(definition)
    assert (
        workflow_hash({**definition, "path": "/tmp/one/workflow.md", "binding": {"workflow": "workflow"}}) == expected
    )
    assert workflow_hash({**definition, "path": "/tmp/two/workflow.md", "ok": True, "errors": []}) == expected
    assert workflow_hash({**definition, "approvals": {"integration": "auto"}}) != expected
    assert workflow_hash({**definition, "stages": [{"id": "review", "exit": []}]}) != expected
