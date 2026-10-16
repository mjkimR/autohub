"""Prepare deterministic work branches and PRs. Issues never supply task inputs."""

import base64
from urllib.parse import quote

import httpx
from app.features.project_management.pipelines.github import (
    GitHubActionsReader,
    GitHubObservationError,
    github_http_error,
)
from app.features.project_management.work_plans.models import WorkItem, WorkPlan


class PreparationRefused(GitHubObservationError):
    """Preparation stops for good before any write; the item needs a different start, not a retry."""

    def __init__(self, message: str):
        super().__init__(message, 422)


class MissingWorkBaseBranch(PreparationRefused):
    """The readable repository has no exact target ref; no preparation writes have begun."""


class ActivityBranchTaken(PreparationRefused):
    """The item's activity branch already exists on the remote and carries work that is not this item's."""


class AttachedBranchMissing(PreparationRefused):
    """An explicitly attached branch is not on the remote; nothing to attach to."""


class WorkGitHub:
    def __init__(self, client: httpx.AsyncClient):
        self.client, self.reader = client, GitHubActionsReader(client)

    async def write(self, method: str, path: str, data: dict) -> dict:
        try:
            response = await self.client.request(method, path, json=data)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as exc:
            raise github_http_error("work synchronization", exc.response) from None
        except (httpx.RequestError, ValueError):
            raise GitHubObservationError("GitHub work request was not confirmed; reconciling before retry") from None

    async def optional(self, path: str, params=None):
        try:
            return await self.reader._get(path, params)
        except GitHubObservationError as exc:
            if exc.status_code == 404:
                return None
            raise

    async def base_sha(self, plan: WorkPlan) -> str:
        root = f"/repos/{plan.repository}/git"
        branch = quote(plan.base_branch, safe="")
        try:
            ref = await self.reader._get(f"{root}/ref/heads/{branch}")
        except GitHubObservationError as exc:
            if exc.status_code != 404 or exc.retry_after:
                raise
            # A private resource can return 404 for missing permissions. Require a
            # successful listing with the same Contents permission before declaring
            # the base absent. Prefix matches are not the requested branch.
            matches = await self.reader._get_list(f"{root}/matching-refs/heads/{branch}")
            ref = next((row for row in matches if row.get("ref") == f"refs/heads/{plan.base_branch}"), None)
            if ref is None:
                raise MissingWorkBaseBranch("Target branch is absent from the repository's readable Git refs") from None
        return ref["object"]["sha"]

    async def prepare(self, plan: WorkPlan, item: WorkItem) -> dict:
        """Start the item's activity branch, or attach to the one the operator named; then its PR.

        A new start refuses an existing remote branch unless it is this item's own earlier attempt (the seed file,
        the marked PR, or an untouched tip at the item's base). An explicit attach never creates the branch and
        adopts an open PR of it whatever its body says.
        """
        root = f"/repos/{plan.repository}"
        branch = item.branch
        attached = item.attach_branch is not None
        seed = f".autohub/work-items/{item.id}.md"
        marker = f"<!-- autohub-work-pr:{item.id} -->"
        ref_path = f"{root}/git/ref/heads/{quote(str(branch), safe='')}"
        ref = await self.optional(ref_path)
        pulls = await self.reader._get_list(
            f"{root}/pulls",
            {
                "head": f"{plan.repository.split('/')[0]}:{branch}",
                "state": "all",
                "per_page": 100,
            },
        )
        pull = next((p for p in pulls if p.get("head", {}).get("ref") == branch), None)
        if attached:
            if ref is None:
                raise AttachedBranchMissing(f"Attached branch {branch} does not exist on the remote; push it first")
            # Attaching adopts the branch's open pull request; a closed one is history, so a new one is opened.
            pull = next((p for p in pulls if p.get("head", {}).get("ref") == branch and p.get("state") == "open"), None)
        elif ref is None:
            await self.write("POST", f"{root}/git/refs", {"ref": f"refs/heads/{branch}", "sha": item.base_sha})
        else:
            ours = (
                (pull is not None and marker in (pull.get("body") or ""))
                or (ref.get("object") or {}).get("sha") == item.base_sha
                or await self.optional(f"{root}/contents/{seed}", {"ref": branch}) is not None
            )
            if not ours:
                raise ActivityBranchTaken(
                    f"Branch {branch} already exists on the remote and is not this item's; attach it explicitly "
                    "with attach_branch, or use another item key"
                )
        if pull:
            if pull.get("base", {}).get("ref") != plan.base_branch:
                raise GitHubObservationError("Reserved work PR identity or target branch changed", 422)
            if not attached and marker not in (pull.get("body") or ""):
                raise GitHubObservationError("Reserved work PR identity or target branch changed", 422)
            return pull
        if await self.optional(f"{root}/contents/{seed}", {"ref": branch}) is None:
            await self.write(
                "PUT",
                f"{root}/contents/{seed}",
                {
                    "message": "Prepare AutoHub work item",
                    "branch": branch,
                    "content": base64.b64encode(f"Pending work item {item.id}\n".encode()).decode(),
                },
            )
        body = (
            f"{item.description}\n\n## Acceptance criteria\n\n{item.acceptance}\n\n"
            f"Remove the preparation file `{seed}` when implementing this task.\n\n"
            f"AutoHub Plan: `{plan.id}` / Item: `{item.key}`\n\n{marker}"
        )
        return await self.write(
            "POST",
            f"{root}/pulls",
            {
                "title": item.title,
                "head": branch,
                "base": plan.base_branch,
                "draft": False,
                "body": body,
            },
        )
