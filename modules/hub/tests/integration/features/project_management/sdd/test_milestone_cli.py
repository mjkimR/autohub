"""Milestone catalog/resolution through the provisioned runtime and real OS isolation."""

import pytest
from app.features.project_management.sdd.milestone_graph import MilestoneGraph
from app.features.project_management.sdd.runtime import restore
from app.features.project_management.sdd.services import cli

from tests.integration.features.execution.flows import test_bridge

pytestmark = pytest.mark.integration
checkout = test_bridge.checkout


async def test_real_isolated_catalog_resolves_archive_members_and_completed_alias(checkout):
    root, _ = checkout
    directory = root / "docs/roadmap/_archive"
    directory.mkdir(parents=True)
    (directory / "MS-fixture.md").write_text(
        '---\nid: MS-fixture\ntitle: Fixture\nsummary: "Archived milestone fixture."\nstatus: done\n---\n# Fixture\n'
    )
    proposal = root / "docs/proposals/PROP-demo"
    proposal.mkdir(parents=True)
    (proposal / "proposal.md").write_text(
        '---\nid: PROP-demo\ntitle: Demo\nsummary: "Direct milestone member."\nstatus: draft\n'
        "milestone: MS-fixture\ndepends_on: [SPEC-retired]\n---\n# Demo\n"
    )
    spec = root / test_bridge.SPEC / "spec.md"
    spec.write_text(spec.read_text().replace("status: completed", "aliases: [SPEC-retired]\nstatus: completed"))
    await restore(root)
    graph = MilestoneGraph(root)
    await graph.load()
    assert not graph.reasons
    milestone = await graph.milestone("MS-fixture", "docs/roadmap/_archive/MS-fixture.md")
    members = await graph.members(milestone)
    assert [member["id"] for member in members] == ["PROP-demo"]
    assert any(row["id"] == "SPEC-fixture" for row in graph.documents), graph.documents
    assert await graph.dependencies(members[0]) == []
    assert graph.edges[0]["canonical_id"] == "SPEC-fixture"
    assert graph.edges[0]["path"] == f"{test_bridge.SPEC}/spec.md"
    assert (await cli(root, "spec", "policy"))["development"]["approach"] == "sdd"

    # A retired PROP name is not inferred from the completed SPEC's slug or origin.
    (proposal / "proposal.md").write_text(
        (proposal / "proposal.md").read_text().replace("SPEC-retired", "PROP-retired")
    )
    missing = MilestoneGraph(root)
    await missing.load()
    holds = await missing.dependencies(members[0])
    assert holds and "PROP-retired" in holds[0]
    assert missing.edges[0]["requested_id"] == "PROP-retired"
    assert missing.edges[0]["canonical_id"] is None
    assert missing.reasons


async def test_two_real_branch_snapshots_pin_global_package_archive_and_dependencies(checkout, tmp_path, monkeypatch):
    """GitHub ref observations are doubled; Git snapshots, catalog and OS-isolated CLI are real."""
    import subprocess
    from contextlib import asynccontextmanager
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from uuid import uuid4

    import httpx
    from app.features.project_management.sdd import milestones
    from app.features.project_management.sdd.schemas import MilestonePreviewRequest

    root, _ = checkout

    def git(*args, cwd=root):
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()

    def commit():
        git("add", ".")
        git(
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.com",
            "commit",
            "-qm",
            "Snapshot",
        )
        return git("rev-parse", "HEAD")

    def document(path, identity, status, **fields):
        import yaml

        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(
            "---\n"
            + yaml.safe_dump(
                {"id": identity, "title": identity, "summary": "Pinned fixture.", "status": status, **fields}
            )
            + "---\n# Fixture\n"
        )

    config = root / ".devkit/config.toml"
    config.write_text(config.read_text() + '\n[[tool.docs.namespaces]]\nname = "demo"\npath = "packages/demo"\n')
    (root / "packages/demo").mkdir(parents=True)
    for path, identity in [
        ("docs/roadmap/MS-global.md", "MS-global"),
        ("docs/packages/demo/roadmap/MS-package.md", "MS-package"),
    ]:
        document(path, identity, "active")
    for slug, ms in [("a", "MS-global"), ("pa", "MS-package")]:
        document(
            f"docs/proposals/PROP-{slug}/proposal.md",
            f"PROP-{slug}",
            "draft",
            milestone=ms,
            depends_on=["SPEC-fixture"],
        )
    spec = root / test_bridge.SPEC / "spec.md"
    document(str(spec.relative_to(root)), "SPEC-fixture", "completed", milestone="MS-global")
    first = commit()
    for path in [root / "docs/roadmap/MS-global.md", root / "docs/packages/demo/roadmap/MS-package.md"]:
        archive = path.parent / "_archive"
        archive.mkdir()
        path.rename(archive / path.name)
        identity = path.stem
        document(
            str((archive / path.name).relative_to(root)), identity, "done" if identity == "MS-global" else "dropped"
        )
    document(
        "docs/proposals/PROP-a/proposal.md", "PROP-a", "draft", milestone="MS-package", depends_on=["SPEC-fixture"]
    )
    document("docs/proposals/PROP-b/proposal.md", "PROP-b", "draft", milestone="MS-global", depends_on=["SPEC-fixture"])
    document(str(spec.relative_to(root)), "SPEC-fixture", "planned", milestone="MS-global")
    second = commit()
    git("update-ref", "refs/heads/second", second)
    checked = []

    @asynccontextmanager
    async def pinned(repository, head, base, token):
        assert head == base
        checked.append(head)
        clone = tmp_path / f"snapshot-{len(checked)}"
        git("clone", "--quiet", "--no-hardlinks", str(root), str(clone))
        git("-c", "core.hooksPath=/dev/null", "checkout", "--quiet", "--detach", head, cwd=clone)
        yield clone

    def respond(request):
        assert request.method == "GET"
        if "/commits/" in request.url.path:
            ref = request.url.path.rsplit("/", 1)[1]
            sha = git("rev-parse", ref)
            if ref == "feature":
                git("update-ref", "refs/heads/feature", second)  # remote moves after the SHA was captured
            return httpx.Response(200, json={"sha": sha})
        if "/git/ref/heads/" in request.url.path:
            return httpx.Response(404)
        raise AssertionError(request.url.path)

    monkeypatch.setattr(milestones, "checkout", pinned)
    monkeypatch.setattr(
        milestones.pipeline_services,
        "create_github_client",
        lambda token: httpx.AsyncClient(base_url="https://api.github.com", transport=httpx.MockTransport(respond)),
    )
    project = SimpleNamespace(id=uuid4(), github_repository="owner/repo", github_connector_id=uuid4())
    observer = SimpleNamespace(get_token=AsyncMock(return_value="token"))
    for ref, sha, global_ids, package_ids, dependency_status in [
        ("feature", first, {"PROP-a"}, {"PROP-pa"}, "completed"),
        ("second", second, {"PROP-b"}, {"PROP-a", "PROP-pa"}, "planned"),
    ]:
        for identity, expected in [("MS-global", global_ids), ("MS-package", package_ids)]:
            git("update-ref", "refs/heads/feature", first)
            value = await milestones.preview_milestone(
                observer, project, MilestonePreviewRequest(ref=ref, milestone_id=identity), AsyncMock(return_value=[])
            )
            assert value["resolved_sha"] == sha
            assert {row["id"] for row in value["members"]} == expected
            assert value["nodes"][0]["status"] == dependency_status
            assert value["nodes"][0]["path"] == f"{test_bridge.SPEC}/spec.md"
            assert ("/_archive/" in value["milestone"]["path"]) is (ref == "second")
    assert checked == [first, first, second, second]
