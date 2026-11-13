from unittest.mock import AsyncMock

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import batch_evidence

pytestmark = pytest.mark.unit


async def test_canonical_resolution_requires_exact_completed_anchor_metadata(tmp_path, monkeypatch):
    path = "specs/2026-11/20261106-external/spec.md"
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    target.write_text("---\nid: SPEC-external\nstatus: completed\naliases: [PROP-external]\n---\n# External\n")
    cli = AsyncMock(
        return_value={"documents": [{"id": "SPEC-external", "kind": "spec", "path": path, "status": "completed"}]}
    )
    monkeypatch.setattr(batch_evidence, "cli", cli)
    resolved = await batch_evidence.canonical_resolutions(tmp_path, ["PROP-external"])
    assert resolved["PROP-external"]["id"] == "SPEC-external"
    target.write_text("---\nid: SPEC-external\nstatus: in-progress\n---\n# External\n")
    assert await batch_evidence.canonical_resolutions(tmp_path, ["PROP-external"]) == {}
    cli.reset_mock()
    with pytest.raises(ProjectError):
        await batch_evidence.canonical_resolutions(tmp_path, [f"PROP-{i}" for i in range(201)])
    cli.assert_not_called()


async def test_basis_runtime_is_the_same_identity_across_cache_directories(tmp_path, monkeypatch):
    import json

    from app.features.project_management.sdd import runtime, runtime_cache

    identity = "9" * 64
    repo = tmp_path / "repo"
    (repo / ".devkit").mkdir(parents=True)
    (repo / ".devkit/config.toml").write_text("agents = []\n")
    (repo / "uv.lock").write_text("an unrelated change does not enter the basis\n")
    monkeypatch.setattr(batch_evidence, "cli", AsyncMock(return_value={"approvals": {}}))
    bases = []
    for name in ("instance-a", "instance-b"):
        monkeypatch.setenv("AUTOHUB_SDD_CACHE", str(tmp_path / name))
        home = runtime_cache.entry(identity)
        home.mkdir(parents=True)
        pin = {"provider": "devkit-spec", "identity": identity, "python": "3.13", "python_prefix": f"/{name}"}
        (home / "pin.json").write_text(json.dumps({**pin, "revisions": {"devkit-spec": "a" * 40}}))
        with runtime.runtime_source(repo, None) as source:
            source.home = home
            bases.append(await batch_evidence.capture_basis(repo, None, []))
    assert bases[0]["runtime"] == bases[1]["runtime"]
    assert set(bases[0]["runtime"]) == {"provider", "identity", "python", "revisions"}
    assert "uv.lock" not in bases[0]["configuration"]
