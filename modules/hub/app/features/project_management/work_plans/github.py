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
        ref = await self.reader._get(f"/repos/{plan.repository}/git/ref/heads/{quote(plan.base_branch, safe='')}")
        return ref["object"]["sha"]

    async def prepare(self, plan: WorkPlan, item: WorkItem) -> dict:
        root = f"/repos/{plan.repository}"
        branch = item.branch
        ref_path = f"{root}/git/ref/heads/{quote(str(branch), safe='')}"
        ref = await self.optional(ref_path)
        if ref is None:
            await self.write("POST", f"{root}/git/refs", {"ref": f"refs/heads/{branch}", "sha": item.base_sha})
        seed = f".autohub/work-items/{item.id}.md"
        pulls = await self.reader._get_list(
            f"{root}/pulls",
            {
                "head": f"{plan.repository.split('/')[0]}:{branch}",
                "state": "all",
                "per_page": 100,
            },
        )
        marker = f"<!-- autohub-work-pr:{item.id} -->"
        pull = next((p for p in pulls if p.get("head", {}).get("ref") == branch), None)
        if pull:
            if marker not in (pull.get("body") or "") or pull.get("base", {}).get("ref") != plan.base_branch:
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
