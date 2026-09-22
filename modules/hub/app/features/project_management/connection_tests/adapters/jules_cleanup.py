"""Reconcile and close owned output through GitHub even when Jules credentials no longer work."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from urllib.parse import quote

from app.features.ai_catalogs.providers.jules import JulesApiError
from app.features.project_management.connection_tests.adapters.base import TestContext
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.connection_tests.ownership import confirmed, has_marker, quarantine
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
        if not confirmed(row, number):
            # Older records used ancestry as ownership. Re-establish positive identity before mutating them.
            if (
                has_marker(row, pr)
                and (pr.get("head", {}).get("repo") or {}).get("full_name", "").lower() == row.repository.lower()
            ):
                comparison = await context.github.reader._get(
                    f"/repos/{row.repository}/compare/{row.evidence['initial_sha']}...{pr['head']['sha']}"
                )
                if comparison.get("status") in ("ahead", "identical"):
                    context.github.record_owned_pull(row, pr, proof="marker")
            if not confirmed(row, number):
                quarantine(row, pr)
                continue
        await context.github.mark_pull(row, pr)
        if pr["state"] == "open":
            await context.github.write("PATCH", path, {"state": "closed"})
    if numbers:
        row.evidence["pr_closed"] = all(confirmed(row, number) for number in numbers)


async def discover_outputs(row: ConnectionTest, context: TestContext) -> None:
    if not row.evidence.get("initial_sha"):
        return
    github = context.github
    root = f"/repos/{row.repository}"
    # Provider output is a new PR, but may target any base or omit the requested marker.
    # Walk recent PRs in creation order, allowing for clock skew, instead of filtering by base.
    cutoff = as_utc(row.created_at) - timedelta(minutes=5)
    for page in range(1, 11):
        pulls = await github.reader._get_list(
            f"{root}/pulls",
            {
                "state": "all",
                "sort": "created",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            },
        )
        for pr in pulls:
            created = pr.get("created_at")
            if created and as_utc(datetime.fromisoformat(created)) < cutoff:
                return
            head = pr.get("head") or {}
            if (head.get("repo") or {}).get("full_name", "").lower() != row.repository.lower():
                continue
            comparison = await github.reader._get(f"{root}/compare/{row.evidence['initial_sha']}...{head['sha']}")
            if comparison.get("status") in ("behind", "diverged"):
                continue
            if comparison.get("status") not in ("ahead", "identical"):
                raise GitHubObservationError("GitHub did not establish ownership of a possible test PR")
            if confirmed(row, pr["number"]):
                continue
            if has_marker(row, pr):
                context.github.record_owned_pull(row, pr, proof="marker")
            else:
                # Main may itself contain the test commit after an external merge. Its descendants are
                # not ours to close/delete without a session output or an explicit per-test marker.
                quarantine(row, pr)
        if len(pulls) < 100:
            return
    raise GitHubObservationError("Test PR discovery exceeded its page limit; cleanup will retry")


async def cleanup_jules(row: ConnectionTest, context: TestContext, reconcile: Callable[[], Awaitable[None]]) -> None:
    dispatched = row.evidence.get("create_attempted", row.evidence.get("jules_create_attempted", False))
    if row.evidence.get("cleanup_resolution"):
        row.evidence["provider_output_confirmed"] = True
        row.evidence["execution_finished"] = True
    if dispatched:
        row.evidence.setdefault(
            "provider_output_confirmed",
            bool(row.evidence.get("execution_finished") and row.evidence.get("output_discovery_pending") is False),
        )
        # A failed/incomplete GitHub scan must keep ancestry protection even if the provider is terminal.
        row.evidence["output_discovery_pending"] = True
    await close_known(row, context)
    legacy_numbers = set(row.evidence.get("owned_pulls", {}))
    if row.evidence.get("pull_number"):
        legacy_numbers.add(str(row.evidence["pull_number"]))
    if not row.evidence.get("cleanup_resolution") and any(not confirmed(row, number) for number in legacy_numbers):
        # Legacy completion flags do not prove that the provider actually identified these PRs.
        row.evidence["provider_output_confirmed"] = False
    if dispatched and not row.evidence["provider_output_confirmed"]:
        try:
            # Leave time in the outer step budget for GitHub cleanup during a provider outage.
            async with asyncio.timeout(15):
                await reconcile()
            row.evidence.pop("cleanup_warning", None)
        except (JulesApiError, PipelineConfigurationError, GitHubObservationError, TimeoutError) as exc:
            row.evidence["cleanup_warning"] = str(exc) or "Jules reconciliation timed out"
    # Reconciliation can record known outputs; retain broader protection until the GitHub scan also finishes.
    row.evidence["output_discovery_pending"] = bool(dispatched)
    await discover_outputs(row, context)
    await close_known(row, context)
    row.evidence["output_discovery_pending"] = bool(
        (dispatched and not row.evidence["provider_output_confirmed"]) or row.evidence.get("unconfirmed_pulls")
    )
    if (
        row.status != "succeeded"
        and row.finished_at
        and get_current_utc_time() < as_utc(row.finished_at) + timedelta(days=1)
    ):
        row.cleanup_status = "waiting"
        return
    if row.evidence.get("output_discovery_pending", row.evidence.get("jules_create_attempted", False)):
        row.cleanup_status = "waiting"
        row.evidence.setdefault(
            "cleanup_warning",
            "Output ownership is still unconfirmed; restore provider access or review cleanup. "
            "PR protection and cleanup retries remain active beyond 24 hours",
        )
        return
    root = f"/repos/{row.repository}"
    repository = await context.github.reader._get(root)
    owned = {number: p for number, p in row.evidence.get("owned_pulls", {}).items() if confirmed(row, number)}
    branches = {context.github.branch(row), *(p["branch"] for p in owned.values())}
    if repository["default_branch"] in branches or row.evidence.get("base_ref") in branches:
        raise GitHubObservationError("A test branch is now a protected base; inspect cleanup manually", 422)
    for branch in sorted(b for b in branches if b):
        if await context.github.optional(f"{root}/git/ref/heads/{quote(branch, safe='')}"):
            await context.github.write("DELETE", f"{root}/git/refs/heads/{quote(branch, safe='')}")
    row.evidence["branch_deleted"] = True
    row.evidence["output_discovery_pending"] = False
    row.cleanup_status = "completed"
