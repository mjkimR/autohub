"""Idempotent preparation and cleanup of probe-owned GitHub resources. No merge operation."""

import base64
from datetime import timedelta
from urllib.parse import quote

import httpx
from app.features.project_management.connection_tests.models import TEST_BRANCH_PREFIX, ConnectionTest
from app.features.project_management.connection_tests.ownership import TEST_LABEL, marker
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.pipelines.github import (
    GitHubActionsReader,
    GitHubObservationError,
    github_http_error,
)
from app.features.project_management.pipelines.schemas import PipelineObservationConfig, VerificationConfig
from app_layer_base.utils.time_util import get_current_utc_time


class ConnectionTestGitHub:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.reader = GitHubActionsReader(client)

    async def write(self, method: str, path: str, body: dict | None = None) -> dict:
        try:
            response = await self.client.request(method, path, json=body)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as exc:
            raise github_http_error("connection test", exc.response) from None
        except (httpx.RequestError, ValueError):
            raise GitHubObservationError("GitHub connection test request failed; reconcile on the next tick") from None

    async def optional(self, path: str, params: dict | None = None) -> dict | None:
        try:
            return await self.reader._get(path, params)
        except GitHubObservationError as exc:
            if exc.status_code == 404:
                return None
            raise

    @staticmethod
    def branch(row: ConnectionTest) -> str:
        return f"{TEST_BRANCH_PREFIX}{row.id}"

    @staticmethod
    def fixture(row: ConnectionTest) -> str:
        return f".autohub/connection-tests/{row.id}.txt"

    async def prepare_branch(self, row: ConnectionTest) -> None:
        root, branch = f"/repos/{row.repository}", self.branch(row)
        repository = await self.reader._get(root)
        base = repository["default_branch"]
        row.evidence["base_ref"] = base
        ref = await self.optional(f"{root}/git/ref/heads/{quote(branch, safe='')}")
        if ref is None:
            base_ref = await self.reader._get(f"{root}/git/ref/heads/{quote(base, safe='')}")
            await self.write(
                "POST", f"{root}/git/refs", {"ref": f"refs/heads/{branch}", "sha": base_ref["object"]["sha"]}
            )
        path = f"{root}/contents/{self.fixture(row)}"
        if await self.optional(path, {"ref": branch}) is None:
            await self.write(
                "PUT",
                path,
                {
                    "message": "Prepare AutoHub connection test",
                    "branch": branch,
                    "content": base64.b64encode(f"pending:{row.id}\n".encode()).decode(),
                },
            )
        ref = await self.reader._get(f"{root}/git/ref/heads/{quote(branch, safe='')}")
        row.evidence.setdefault("initial_sha", ref["object"]["sha"])
        row.evidence["branch"] = branch

    async def prepare_draft(self, row: ConnectionTest) -> None:
        root, branch = f"/repos/{row.repository}", self.branch(row)
        base = row.evidence["base_ref"]
        pulls = await self.reader._get_list(
            f"{root}/pulls",
            {
                "head": f"{row.repository.split('/')[0]}:{branch}",
                "state": "all",
                "per_page": 100,
            },
        )
        pr = next((p for p in pulls if p.get("head", {}).get("ref") == branch), None)
        if pr is None:
            pr = await self.write(
                "POST",
                f"{root}/pulls",
                {
                    "title": "AutoHub connection test — never merge",
                    "head": branch,
                    "base": base,
                    "draft": True,
                    "body": f"Connection test {row.id}. AutoHub will close this PR. Do not merge or push to this branch.\n\n{marker(row)}",
                },
            )
        row.evidence.update(pull_number=pr["number"], pull_url=pr["html_url"], branch=branch)
        self.record_owned_pull(row, pr, proof="reserved_branch")
        await self.mark_pull(row, pr)
        if pr["state"] != "open":
            raise GitHubObservationError("The connection test PR was already closed", 422)
        row.phase = "dispatching"

    async def observe(self, row: ConnectionTest, *, expected_branch: str) -> None:
        root, number = f"/repos/{row.repository}", row.evidence["pull_number"]
        pr = await self.reader._get(f"{root}/pulls/{number}")
        if pr["state"] != "open":
            row.status, row.detail = "failed", "Test PR was closed before verification finished"
            return
        if pr["head"]["ref"] != expected_branch:
            row.status, row.detail = "failed", "Test PR branch no longer matches"
            return
        head = pr["head"]["sha"]
        if head == row.evidence["initial_sha"]:
            return
        content = await self.optional(f"{root}/contents/{self.fixture(row)}", {"ref": head})
        if content is None or content.get("encoding") != "base64":
            return
        if base64.b64decode(content.get("content", "")) != f"verified:{row.id}\n".encode():
            row.detail = "Head changed, but the requested test marker has not been verified"
            return
        row.evidence["verified_sha"] = head
        row.phase = "verifying_ci"
        config = PipelineObservationConfig(
            repository=row.repository,
            github_connector_id=row.connector_id,
            verification=VerificationConfig.model_validate(row.verification),
            pull_numbers=[number],
        )
        observed = await self.reader.observe_pull(config, number)
        row.evidence["ci_status"] = observed.result.status
        row.evidence["ci_url"] = observed.run.url if observed.run else None
        row.detail = observed.result.reason
        if observed.head_sha != head:
            return
        if observed.result.status == "passed":
            row.status, row.phase, row.detail = "succeeded", "verified", "Test change was pushed and required CI passed"
        elif observed.result.status == "failed":
            row.status = "failed"

    async def cleanup(self, row: ConnectionTest) -> None:
        """Reconcile even a preparation request whose response was lost. Never delete other branches."""
        root, branch = f"/repos/{row.repository}", self.branch(row)
        repository = await self.reader._get(root)
        if repository["default_branch"] == branch:
            raise GitHubObservationError("Test branch is now the default branch; automatic cleanup stopped", 422)
        pulls = await self.reader._get_list(
            f"{root}/pulls",
            {
                "head": f"{row.repository.split('/')[0]}:{branch}",
                "state": "all",
                "per_page": 100,
            },
        )
        for pr in pulls:
            if pr.get("head", {}).get("ref") != branch:
                continue
            row.evidence.update(pull_number=pr["number"], pull_url=pr["html_url"])
            if pr["state"] == "open":
                await self.write("PATCH", f"{root}/pulls/{pr['number']}", {"state": "closed"})
        row.evidence["pr_closed"] = True
        # A canceled Hub request cannot stop an already running cloud agent. Leave its isolated branch
        # for a day before deleting it; the test remains terminal throughout this cleanup window.
        if (
            row.status != "succeeded"
            and row.finished_at
            and get_current_utc_time() < as_utc(row.finished_at) + timedelta(days=1)
        ):
            row.cleanup_status = "waiting"
            return
        ref_path = f"{root}/git/ref/heads/{quote(branch, safe='')}"
        if await self.optional(ref_path) is not None:
            await self.write("DELETE", f"{root}/git/refs/heads/{quote(branch, safe='')}")
        row.evidence["branch_deleted"] = True
        row.cleanup_status = "completed"

    @staticmethod
    def record_owned_pull(row: ConnectionTest, pr: dict, *, proof: str) -> None:
        number, branch, url = pr["number"], pr["head"]["ref"], pr["html_url"]
        row.evidence.update(pull_number=number, pull_url=url, output_branch=branch)
        row.evidence.setdefault("owned_pulls", {})[str(number)] = {
            "branch": branch,
            "url": url,
            "sha": pr["head"]["sha"],
            "proof": proof,
        }
        row.evidence.get("unconfirmed_pulls", {}).pop(str(number), None)

    async def mark_pull(self, row: ConnectionTest, pr: dict) -> None:
        """Best-effort visible metadata; persisted ownership does not depend on label permissions."""
        root, number = f"/repos/{row.repository}", pr["number"]
        try:
            body = pr.get("body") or ""
            if marker(row) not in body:
                await self.write("PATCH", f"{root}/pulls/{number}", {"body": f"{body}\n\n{marker(row)}"})
            if TEST_LABEL not in {label.get("name") for label in pr.get("labels", [])}:
                label_path = f"{root}/labels/{TEST_LABEL}"
                if await self.optional(label_path) is None:
                    try:
                        await self.write("POST", f"{root}/labels", {"name": TEST_LABEL, "color": "d93f0b"})
                    except GitHubObservationError as exc:
                        if exc.status_code != 422 or await self.optional(label_path) is None:
                            raise
                await self.write("POST", f"{root}/issues/{number}/labels", {"labels": [TEST_LABEL]})
            row.evidence.get("marking_warnings", {}).pop(str(number), None)
        except GitHubObservationError as exc:
            row.evidence.setdefault("marking_warnings", {})[str(number)] = str(exc)
