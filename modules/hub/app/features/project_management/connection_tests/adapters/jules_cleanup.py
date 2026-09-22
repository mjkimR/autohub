"""Reconcile and close owned output through GitHub even when Jules credentials no longer work."""

from collections.abc import Awaitable, Callable
from datetime import timedelta
from urllib.parse import quote

from app.features.ai_catalogs.providers.jules import JulesApiError
from app.features.project_management.connection_tests.adapters.base import TestContext
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.pipelines.github import GitHubObservationError
from app.features.project_management.pipelines.services import PipelineConfigurationError
from app_layer_base.utils.time_util import get_current_utc_time


async def close_known(row: ConnectionTest, context: TestContext) -> None:
    numbers = set(row.evidence.get("owned_pulls", {}))
    if row.evidence.get("pull_number"):
        numbers.add(str(row.evidence["pull_number"]))
    for number in sorted(numbers):
        path = f"/repos/{row.repository}/pulls/{int(number)}"
        pr = await context.github.reader._get(path)
        if pr["state"] == "open":
            await context.github.write("PATCH", path, {"state": "closed"})
    if numbers:
        row.evidence["pr_closed"] = True


async def discover_outputs(row: ConnectionTest, context: TestContext) -> None:
    if not row.evidence.get("initial_sha"):
        return
    github = context.github
    root = f"/repos/{row.repository}"
    for page in range(1, 11):
        pulls = await github.reader._get_list(
            f"{root}/pulls",
            {
                "base": github.branch(row),
                "state": "all",
                "per_page": 100,
                "page": page,
            },
        )
        for pr in pulls:
            if pr.get("base", {}).get("ref") != github.branch(row):
                continue
            head = pr.get("head") or {}
            if (head.get("repo") or {}).get("full_name", "").lower() != row.repository.lower():
                continue
            comparison = await github.reader._get(f"{root}/compare/{row.evidence['initial_sha']}...{head['sha']}")
            if comparison.get("status") not in ("ahead", "identical"):
                continue
            context.github.record_owned_pull(row, pr)
        if len(pulls) < 100:
            return
    raise GitHubObservationError("Test PR discovery exceeded its page limit; cleanup will retry")


async def cleanup_jules(row: ConnectionTest, context: TestContext, reconcile: Callable[[], Awaitable[None]]) -> None:
    await close_known(row, context)
    if row.evidence.get("create_attempted", row.evidence.get("jules_create_attempted")) and row.evidence.get(
        "output_discovery_pending", True
    ):
        try:
            await reconcile()
        except (JulesApiError, PipelineConfigurationError, TimeoutError) as exc:
            row.evidence["cleanup_warning"] = str(exc) or "Jules reconciliation timed out"
            if isinstance(exc, JulesApiError) and exc.status_code == 404:
                row.evidence["execution_finished"] = True
    await discover_outputs(row, context)
    await close_known(row, context)
    if (
        row.status != "succeeded"
        and row.finished_at
        and get_current_utc_time() < as_utc(row.finished_at) + timedelta(days=1)
    ):
        row.cleanup_status = "waiting"
        return
    root = f"/repos/{row.repository}"
    repository = await context.github.reader._get(root)
    branches = {context.github.branch(row), row.evidence.get("output_branch")}
    branches.update(p["branch"] for p in row.evidence.get("owned_pulls", {}).values())
    if repository["default_branch"] in branches or row.evidence.get("base_ref") in branches:
        raise GitHubObservationError("A test branch is now a protected base; inspect cleanup manually", 422)
    for branch in sorted(b for b in branches if b):
        if await context.github.optional(f"{root}/git/ref/heads/{quote(branch, safe='')}"):
            await context.github.write("DELETE", f"{root}/git/refs/heads/{quote(branch, safe='')}")
    row.evidence["branch_deleted"] = True
    row.evidence["output_discovery_pending"] = False
    row.cleanup_status = "completed"
