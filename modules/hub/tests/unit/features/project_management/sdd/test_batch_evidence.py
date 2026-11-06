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
