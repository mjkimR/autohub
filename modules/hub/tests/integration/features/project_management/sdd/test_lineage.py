"""Related executions use recorded handoffs, with exact project boundaries."""

from uuid import UUID, uuid4

import pytest
from app.features.project_management.pipeline_runs.models import PipelineRun
from app_layer_base.core.database.transaction import AsyncTransaction

from tests.integration.features.project_management.sdd import test_native as scenarios

github = scenarios.github
project = scenarios.project
inspector = scenarios.inspector
unit_branch = scenarios.unit_branch
run = scenarios.run
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_proposal_spec_run_and_pr_lineage_uses_recorded_project_scoped_handoffs(client, project, run):
    other = await client.post("/api/v1/projects", json={"name": "Other", "project_type": "sdd"})
    assert other.status_code == 201, other.text
    origin = "docs/proposals/PROP-origin"
    ids = [uuid4() for _ in range(4)]
    async with AsyncTransaction() as session:
        source = await session.get(PipelineRun, UUID(run["id"]))
        values = {
            field: getattr(source, field)
            for field in (
                "ai_catalog_id",
                "project_revision",
                "github_repository",
                "github_connector_id",
                "pull_url",
                "pull_snapshot",
                "branch",
            )
        }
        for index, (project_id, snapshot) in enumerate(
            [
                (project["id"], {"spec_dir": origin}),
                (project["id"], {"spec_dir": scenarios.SPEC, "handoff_from": origin}),
                (project["id"], {"spec_dir": "specs/2026-10/same-slug-without-handoff"}),
                (other.json()["id"], {"spec_dir": scenarios.SPEC, "handoff_from": origin}),
            ]
        ):
            session.add(
                PipelineRun(
                    **values,
                    id=ids[index],
                    project_id=UUID(project_id),
                    pull_number=100 + index,
                    state="completed",
                    sdd_snapshot=snapshot,
                )
            )
    path = f"/api/v1/projects/{project['id']}/sdd/runs"
    for unit, expected in [
        (origin, {str(ids[0]), str(ids[1])}),
        (scenarios.SPEC, {run["id"], str(ids[0]), str(ids[1])}),
    ]:
        result = await client.get(path, params={"spec_dir": unit})
        assert result.status_code == 200, result.text
        assert {row["id"] for row in result.json()} == expected
        assert all(row["project_id"] == project["id"] for row in result.json())
