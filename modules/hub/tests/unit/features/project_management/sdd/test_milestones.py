"""Pinned read-only readiness and exact scheduling contract fixtures."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
import yaml
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import activities, milestone_graph, milestones, policy, services
from app.features.project_management.sdd.schemas import MilestonePreview, MilestonePreviewRequest

pytestmark = pytest.mark.unit
SHA = "a" * 40


@pytest.fixture
def preview(tmp_path, monkeypatch):
    documents, aliases, currents, refs, pulls, calls = [], {}, {}, {}, [], []

    def add(identity, kind="proposal", status="draft", **meta):
        path = (
            f"docs/proposals/{identity}/proposal.md"
            if kind == "proposal"
            else f"docs/roadmap/{identity}.md"
            if kind == "milestone"
            else f"specs/2026-11/demo/{identity}/spec.md"
        )
        path = meta.pop("path", path)
        row = {"id": identity, "kind": kind, "status": status, "path": path, "title": identity}
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("---\n" + yaml.safe_dump({**row, **meta}) + "---\n# Anchor\n")
        documents.append(row)
        return row

    add("MS-demo", "milestone", "planned")
    add("PROP-demo", milestone="MS-demo")

    async def cli(root, *args):
        calls.append(("cli", args))
        assert root == tmp_path
        if args[:2] == ("docs", "list"):
            return {"documents": documents, "total": len(documents)}
        if args[:2] == ("docs", "resolve"):
            identity = aliases.get(args[2], args[2])
            rows = [row for row in documents if row["id"] == identity]
            return {"documents": rows, "errors": []}
        if args[:2] == ("spec", "policy"):
            return {"development": {"approach": refs.get("approach", "sdd")}}
        if args[:2] == ("workflow", "next"):
            return {"done": ["intent-proposal"], "stage": {"id": "direction"}, **currents.get(args[-1], {})}
        raise AssertionError(args)

    monkeypatch.setattr(milestone_graph, "cli", cli)
    monkeypatch.setattr(milestones, "cli", cli)
    monkeypatch.setattr(services, "cli", cli)

    @asynccontextmanager
    async def checkout(repository, head, base, token):
        calls.append(("checkout", head, base))
        assert head == base == SHA
        yield tmp_path

    async def restore(root):
        calls.append(("restore", root))
        return []

    monkeypatch.setattr(milestones, "checkout", checkout)
    monkeypatch.setattr(milestones, "restore", restore)
    monkeypatch.setattr(milestones, "configured_version", lambda: "devkit-spec:locked")

    def respond(request):
        calls.append((request.method, request.url.path))
        assert request.method == "GET", "Preview must never write GitHub"
        path = request.url.path.removeprefix("/repos/owner/repo")
        if path == "/commits/feature":
            return httpx.Response(200, json={"sha": SHA})
        if path.startswith("/git/ref/heads/"):
            return (
                httpx.Response(200, json={"object": {"sha": "b" * 40}})
                if refs.get(path.split("/")[-1])
                else httpx.Response(404)
            )
        if path == "/pulls":
            return httpx.Response(200, json=pulls)
        raise AssertionError(path)

    monkeypatch.setattr(
        milestones.pipeline_services,
        "create_github_client",
        lambda token: httpx.AsyncClient(base_url="https://api.github.com", transport=httpx.MockTransport(respond)),
    )
    forbidden = AsyncMock(side_effect=AssertionError("Execution collaborator called"))
    monkeypatch.setattr(activities, "start_branch", forbidden)
    project = SimpleNamespace(id=uuid4(), github_repository="owner/repo", github_connector_id=uuid4())
    observer = SimpleNamespace(get_token=AsyncMock(return_value="token"))
    runs = AsyncMock(return_value=[])

    async def run(**overrides):
        request = MilestonePreviewRequest(ref="feature", milestone_id="MS-demo", **overrides)
        result = await milestones.preview_milestone(observer, project, request, runs)
        MilestonePreview.model_validate(result)
        forbidden.assert_not_called()
        return result

    return SimpleNamespace(
        run=run,
        add=add,
        documents=documents,
        aliases=aliases,
        currents=currents,
        refs=refs,
        pulls=pulls,
        calls=calls,
        runs=runs,
        root=tmp_path,
    )


async def test_pinned_complete_preview_is_read_only_and_restores_once(preview):
    before = {p: p.read_bytes() for p in preview.root.rglob("*.md")}
    result = await preview.run()
    assert result["complete"] and result["resolved_sha"] == SHA
    assert result["members"][0]["eligibility"] == "eligible_now"
    assert result["members"][0]["admission"] == result["members"][0]["scheduling"] == "pass"
    assert len([c for c in preview.calls if c[0] == "restore"]) == 1
    assert before == {p: p.read_bytes() for p in preview.root.rglob("*.md")}
    preview.runs.assert_not_called()


@pytest.mark.parametrize(
    "status,expected",
    [
        ("draft", "eligible_now"),
        ("accepted", "eligible_now"),
        ("reviewing", "unsupported"),
        ("rejected", "unsupported"),
        ("handed_off", "finished"),
    ],
)
async def test_status_admission_parity(preview, status, expected):
    preview.documents.pop()
    row = preview.add("PROP-demo", status=status, milestone="MS-demo")
    result = await preview.run()
    member = result["members"][0]
    assert member["eligibility"] == expected
    if status in ("draft", "accepted"):
        activity = member["activity_kind"]
        assert activities.admission_reason((preview.root / row["path"]).read_text(), activity, "demo") is None


@pytest.mark.parametrize("status", ["draft", "accepted"])
@pytest.mark.parametrize(
    "hold",
    [
        {"blocked": True},
        {"pending_questions": [{"file": "worker-01.yaml", "id": "q"}]},
        {"malformed_workers": [{"file": "worker-01.yaml", "reason": "invalid"}]},
    ],
)
async def test_done_intent_never_hides_worker_holds(preview, status, hold):
    preview.documents.pop()
    preview.add("PROP-demo", status=status, milestone="MS-demo")
    preview.currents["docs/proposals/PROP-demo"] = hold
    result = await preview.run()
    assert result["members"][0]["eligibility"] == "held"
    # Scheduling/workflow hold is additional observation, not a new individual start gate.
    assert await policy.admission_blocker(preview.root, "docs/proposals/PROP-demo", "dev") is None


async def test_inactive_lifecycle_and_partial_runtime_are_not_ready(preview, monkeypatch):
    preview.refs["approach"] = "adaptive-dev"
    result = await preview.run()
    assert result["members"][0]["eligibility"] == "held"
    monkeypatch.setattr(milestones, "restore", AsyncMock(side_effect=ProjectError(422, "No runtime")))
    result = await preview.run()
    assert not result["complete"] and not result["members"] and result["reasons"]


@pytest.mark.parametrize(
    "kind,status,expected",
    [
        ("milestone", "done", "pass"),
        ("milestone", "dropped", "pass"),
        ("spec", "completed", "pass"),
        ("proposal", "accepted", "held"),
        ("spec", "planned", "held"),
    ],
)
async def test_exact_dependency_semantics(preview, kind, status, expected):
    identity = {"milestone": "MS-before", "spec": "SPEC-before", "proposal": "PROP-before"}[kind]
    preview.add(identity, kind, status, depends_on=["MISSING-history"] if status == "completed" else [])
    owner = "MS-demo" if kind == "milestone" else "PROP-demo"
    row = next(r for r in preview.documents if r["id"] == owner)
    file = preview.root / row["path"]
    file.write_text(file.read_text().replace("---\n# Anchor", f"depends_on: [{identity}]\n---\n# Anchor"))
    result = await preview.run()
    assert result["members"][0]["scheduling"] == expected
    assert len(result["edges"]) == 1


async def test_no_guessed_handoff_and_explicit_alias_resolution(preview):
    preview.add("SPEC-demo", "spec", "completed", handoff_from="PROP-old")
    row = preview.documents[1]
    file = preview.root / row["path"]
    file.write_text(file.read_text().replace("---\n# Anchor", "depends_on: [PROP-old]\n---\n# Anchor"))
    result = await preview.run()
    assert result["members"][0]["scheduling"] == "held"
    preview.aliases["PROP-old"] = "SPEC-demo"
    result = await preview.run()
    assert result["members"][0]["eligibility"] == "eligible_now"


@pytest.mark.parametrize("count,complete", [(50, True), (51, False)])
async def test_member_exact_boundary(preview, count, complete):
    for number in range(1, count):
        preview.add(f"PROP-unit-{number:03}", milestone="MS-demo")
    result = await preview.run()
    assert result["complete"] is complete and result["counts"]["members"] == count
    assert len(result["members"]) == 50
    if not complete:
        assert all(r["eligibility"] != "eligible_now" for r in result["members"])


@pytest.mark.parametrize("count,complete", [(200, True), (201, False)])
async def test_anchor_exact_boundary(preview, count, complete):
    ids = [f"SPEC-before-{i}" for i in range(count)]
    for identity in ids:
        preview.add(identity, "spec", "completed")
    file = preview.root / preview.documents[1]["path"]
    file.write_text(file.read_text().replace("---\n# Anchor", "depends_on: " + str(ids) + "\n---\n# Anchor"))
    result = await preview.run()
    assert result["complete"] is complete and result["counts"]["anchors"] == count


@pytest.mark.parametrize("count,complete", [(500, True), (501, False)])
async def test_edge_exact_boundary(preview, count, complete):
    preview.add("SPEC-before", "spec", "completed")
    ids = ["SPEC-before"] * count
    file = preview.root / preview.documents[1]["path"]
    file.write_text(file.read_text().replace("---\n# Anchor", "depends_on: " + str(ids) + "\n---\n# Anchor"))
    result = await preview.run()
    assert result["complete"] is complete and result["counts"]["edges"] == count


async def test_existing_owned_activity_is_inspect_only_and_conflict_does_not_link(preview):
    preview.refs["plan-demo"] = True
    result = await preview.run()
    assert result["members"][0]["eligibility"] == "held"
    assert "SDD_BRANCH_EXISTS" in result["members"][0]["reasons"]
    preview.pulls.append({"number": 3, "head": {"ref": "plan-demo"}, "body": activities.marker("plan", "demo")})
    preview.runs.return_value = [SimpleNamespace(id="run", pull_number=3, sdd_progress={"head_sha": "b" * 40})]
    result = await preview.run()
    assert result["members"][0]["eligibility"] == "existing_activity"
    assert result["members"][0]["evidence"][1]["run_id"] == "run"


@pytest.mark.parametrize("path", ["../docs/MS-demo.md", "/docs/MS-demo.md", "docs/../MS-demo.md", "docs\\MS-demo.md"])
async def test_invalid_paths_refuse_before_checkout(preview, path):
    with pytest.raises(ProjectError):
        await preview.run(milestone_path=path)
    assert not preview.calls


async def test_cycles_and_malformed_dependencies_disclose_incomplete_graph(preview):
    file = preview.root / preview.documents[1]["path"]
    original = file.read_text()
    file.write_text(original.replace("---\n# Anchor", "depends_on: [PROP-demo]\n---\n# Anchor"))
    result = await preview.run()
    assert not result["complete"] and any("cycle" in reason for reason in result["reasons"])
    file.write_text(original.replace("---\n# Anchor", "depends_on: invalid\n---\n# Anchor"))
    result = await preview.run()
    assert not result["complete"] and any("Malformed depends_on" in reason for reason in result["reasons"])


async def test_missing_or_ambiguous_milestone_refuses(preview):
    preview.documents.pop(0)
    with pytest.raises(ProjectError, match="missing, ambiguous"):
        await preview.run()
    preview.add("MS-demo", "milestone", "planned")
    preview.add("MS-demo", "milestone", "active", path="docs/roadmap/_archive/MS-demo.md")
    with pytest.raises(ProjectError, match="missing, ambiguous"):
        await preview.run()


async def test_catalog_partial_enumeration_and_deadline_disclose_incomplete(preview, monkeypatch):
    original = milestone_graph.cli

    async def partial(root, *args):
        value = await original(root, *args)
        if args[:2] == ("docs", "list"):
            value["total"] += 1
        return value

    monkeypatch.setattr(milestone_graph, "cli", partial)
    result = await preview.run()
    assert not result["complete"] and "Document catalog coverage is incomplete" in result["reasons"]
    monkeypatch.setattr(milestones, "restore", AsyncMock(side_effect=TimeoutError()))
    result = await preview.run()
    assert not result["complete"] and "Preview deadline exceeded" in result["reasons"]


async def test_pr_pagination_failure_is_partial_and_never_selectable(preview, monkeypatch):
    preview.refs["plan-demo"] = True
    monkeypatch.setattr(
        milestones.WorkGitHub, "optional", AsyncMock(side_effect=[{"sha": SHA}, {"object": {"sha": SHA}}])
    )
    monkeypatch.setattr(
        "app.features.project_management.pipelines.github.GitHubActionsReader._get_list",
        AsyncMock(side_effect=milestones.GitHubObservationError("Pagination failed")),
    )
    result = await preview.run()
    assert not result["complete"] and result["members"][0]["eligibility"] == "unknown"


async def test_archive_package_membership_and_historical_spec_exclusion(preview):
    preview.documents.pop(0)
    preview.add("MS-demo", "milestone", "dropped", path="docs/packages/demo/roadmap/_archive/MS-demo.md")
    preview.add("SPEC-old", "spec", "completed", milestone="MS-demo")
    preview.add("PROP-package", milestone="MS-demo", path="docs/packages/demo/proposals/PROP-package/proposal.md")
    result = await preview.run()
    assert {row["id"] for row in result["members"]} == {"PROP-demo", "PROP-package"}
    assert all(row["eligibility"] != "eligible_now" for row in result["members"])
    assert next(row for row in result["members"] if row["id"] == "PROP-package")["eligibility"] == "unsupported"


async def test_nonanchor_dependency_is_structurally_incomplete(preview):
    preview.add("PROP-blueprint", status="draft", path="docs/proposals/PROP-other/target-docs.md")
    file = preview.root / preview.documents[1]["path"]
    file.write_text(file.read_text().replace("---\n# Anchor", "depends_on: [PROP-blueprint]\n---\n# Anchor"))
    result = await preview.run()
    assert not result["complete"]
    assert result["edges"][0]["path"].endswith("target-docs.md")


async def test_owned_pr_without_run_retains_exact_pr_revisions(preview):
    preview.refs["plan-demo"] = True
    preview.pulls.append(
        {
            "number": 19,
            "head": {"ref": "plan-demo", "sha": "b" * 40},
            "base": {"sha": SHA},
            "body": activities.marker("plan", "demo"),
        }
    )
    result = await preview.run()
    member = result["members"][0]
    assert member["eligibility"] == "existing_activity"
    assert member["evidence"] == [{"pull_number": 19, "head_sha": "b" * 40, "base_sha": SHA, "kind": "pull_request"}]
    assert member["evidence_observed_at"]


@pytest.mark.parametrize("failure", [OSError("runtime missing"), milestones.GitHubObservationError("network")])
async def test_outer_runtime_and_observation_errors_are_incomplete(preview, monkeypatch, failure):
    monkeypatch.setattr(milestones, "restore", AsyncMock(side_effect=failure))
    result = await preview.run()
    assert not result["complete"] and type(failure).__name__ in result["reasons"][0]


@pytest.mark.parametrize("mode", ["owned_second", "failure_second", "exhausted"])
async def test_full_pr_pages_are_never_silently_complete(preview, monkeypatch, mode):
    preview.refs["plan-demo"] = True
    pages = []

    async def listing(reader, path, params):
        pages.append(params["page"])
        if params["page"] == 1 or mode == "exhausted":
            return [{"number": i, "head": {"ref": "plan-demo"}, "body": "unowned"} for i in range(100)]
        if mode == "failure_second":
            raise milestones.GitHubObservationError("Pagination failed")
        return [{"number": 19, "head": {"ref": "plan-demo"}, "body": activities.marker("plan", "demo")}]

    monkeypatch.setattr("app.features.project_management.pipelines.github.GitHubActionsReader._get_list", listing)
    result = await preview.run()
    assert pages == (list(range(1, 11)) if mode == "exhausted" else [1, 2])
    assert result["complete"] is (mode == "owned_second")
    assert result["members"][0]["eligibility"] == ("existing_activity" if mode == "owned_second" else "unknown")


async def test_flat_member_is_inspect_only_and_valid_held_prerequisite(preview):
    preview.add("PROP-before", status="accepted", milestone="MS-demo", path="docs/proposals/PROP-before.md")
    file = preview.root / preview.documents[1]["path"]
    file.write_text(file.read_text().replace("---\n# Anchor", "depends_on: [PROP-before]\n---\n# Anchor"))
    result = await preview.run()
    assert result["complete"]
    members = {member["id"]: member for member in result["members"]}
    assert members["PROP-before"]["eligibility"] == "unsupported"
    assert members["PROP-demo"]["eligibility"] == "held"
    assert result["edges"][0]["path"] == "docs/proposals/PROP-before.md"
