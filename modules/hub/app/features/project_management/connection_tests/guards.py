"""Recognize probe PRs before a provider's output has been discovered by the scheduler."""

from app.features.project_management.connection_tests.models import TEST_BRANCH_PREFIX
from app.features.project_management.connection_tests.ownership import TEST_LABEL
from app.features.project_management.pipelines.github import GitHubActionsReader, GitHubObservationError
from app.features.project_management.projects.errors import ProjectError


def reject_test_refs(pr: dict) -> None:
    if (
        any(str(pr.get(side, {}).get("ref", "")).startswith(TEST_BRANCH_PREFIX) for side in ("head", "base"))
        or str(pr.get("base_ref", "")).startswith(TEST_BRANCH_PREFIX)
        or "hub-connection-test:" in f"{pr.get('title', '')}\n{pr.get('body', '')}"
        or any(label.get("name") == TEST_LABEL for label in pr.get("labels", []) if isinstance(label, dict))
    ):
        raise ProjectError(422, "Connection test pull requests cannot enter development or merge execution")


async def reject_test_ancestry(reader: GitHubActionsReader, repository: str, head: str, test_heads: list[str]) -> None:
    # Jules chooses its output branch name. Its immutable starting commit is saved before session creation,
    # so discovery latency, changing the PR base/title, or removing the fixture cannot enable auto-merge.
    for initial_sha in test_heads:
        try:
            comparison = await reader._get(f"/repos/{repository}/compare/{initial_sha}...{head}")
        except GitHubObservationError as exc:
            raise ProjectError(502, str(exc), code=f"GITHUB_{exc.kind.upper()}") from None
        if comparison.get("status") in ("ahead", "identical"):
            raise ProjectError(422, "Connection test pull requests cannot enter development or merge execution")
        if comparison.get("status") not in ("behind", "diverged"):
            raise ProjectError(502, "GitHub did not establish whether the PR contains a connection test")
