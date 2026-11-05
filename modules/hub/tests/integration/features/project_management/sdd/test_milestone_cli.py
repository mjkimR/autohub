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
