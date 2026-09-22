"""GitHub Actions adapter. It never checks out or executes repository code."""

import time
from typing import Any
from urllib.parse import quote

import httpx
from app.features.project_management.pipelines.gate import evaluate_verification
from app.features.project_management.pipelines.logs import failure_log_excerpt
from app.features.project_management.pipelines.schemas import (
    JobSnapshot,
    PipelineObservationConfig,
    PullObservation,
    RunSnapshot,
    VerificationResult,
    VerificationStatus,
)

GITHUB_FAILURE_AUTH = "auth"
GITHUB_FAILURE_RATE_LIMITED = "rate_limited"
GITHUB_FAILURE_UPSTREAM = "upstream"
# GitHub asks for at least a minute after a secondary rate limit that names no delay.
DEFAULT_RATE_LIMIT_DELAY_SECONDS = 60
MAX_RATE_LIMIT_DELAY_SECONDS = 3600


class GitHubObservationError(RuntimeError):
    """Sanitized upstream failure: no response body, credentials, or request headers.

    ``kind`` tells a caller what would help: new credentials ("auth"), waiting ``retry_after`` seconds
    ("rate_limited"), or nothing it can know ("upstream").
    """

    # The message names only the operation and the HTTP status, so a failed job may show it to its operator.
    operator_safe = True

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        *,
        kind: str = GITHUB_FAILURE_UPSTREAM,
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.kind = kind
        self.retry_after = retry_after


def github_http_error(context: str, response: httpx.Response, now: float | None = None) -> GitHubObservationError:
    """Classify a failed response from its status and rate-limit headers, never from its body."""
    status = response.status_code
    headers = response.headers
    message = f"GitHub {context} returned HTTP {status}"
    if status == 401:
        return GitHubObservationError(message, status, kind=GITHUB_FAILURE_AUTH)
    exhausted = headers.get("x-ratelimit-remaining") == "0"
    if status == 429 or (status in (403, 422) and (exhausted or "retry-after" in headers)):
        delay = DEFAULT_RATE_LIMIT_DELAY_SECONDS
        try:
            if "retry-after" in headers:
                delay = int(headers["retry-after"])
            elif exhausted and "x-ratelimit-reset" in headers:
                delay = int(headers["x-ratelimit-reset"]) - int(time.time() if now is None else now)
        except ValueError:
            pass
        delay = max(DEFAULT_RATE_LIMIT_DELAY_SECONDS, min(delay, MAX_RATE_LIMIT_DELAY_SECONDS))
        return GitHubObservationError(message, status, kind=GITHUB_FAILURE_RATE_LIMITED, retry_after=delay)
    return GitHubObservationError(message, status)


def create_github_client(token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://api.github.com",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=10,
        follow_redirects=False,
    )


class GitHubActionsReader:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def _get(self, path: str, params: dict[str, str | int] | None = None) -> dict[str, Any]:
        try:
            response = await self.client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise github_http_error("observation", exc.response) from None
        except httpx.RequestError:
            raise GitHubObservationError("GitHub observation request failed") from None
        try:
            value = response.json()
        except ValueError:
            raise GitHubObservationError("GitHub observation returned invalid JSON") from None
        if not isinstance(value, dict):
            raise GitHubObservationError("GitHub observation returned an invalid object")
        return value

    async def _get_list(self, path: str, params: dict[str, str | int] | None = None) -> list[dict[str, Any]]:
        try:
            response = await self.client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise github_http_error("observation", exc.response) from None
        except httpx.RequestError:
            raise GitHubObservationError("GitHub observation request failed") from None
        try:
            value = response.json()
        except ValueError:
            raise GitHubObservationError("GitHub observation returned invalid JSON") from None
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise GitHubObservationError("GitHub observation returned an invalid list")
        return value

    async def job_log_excerpt(self, repository: str, job_id: int, *, max_chars: int = 2_000) -> str | None:
        """Read the bounded plain-text log behind GitHub's short-lived redirect."""
        if job_id <= 0 or max_chars <= 0:
            return None
        response = None
        try:
            request = self.client.build_request("GET", f"/repos/{repository}/actions/jobs/{job_id}/logs")
            response = await self.client.send(request, stream=True, follow_redirects=False)
            if response.status_code == 302:
                location = httpx.URL(response.headers.get("location", ""))
                if location.scheme != "https" or not location.host or location.username or location.password:
                    raise GitHubObservationError("GitHub job log returned an invalid download URL")
                await response.aclose()
                request = self.client.build_request("GET", location)
                # The signed URL carries its own authorization; never forward the PAT or cookies.
                request.headers.pop("authorization", None)
                request.headers.pop("cookie", None)
                response = await self.client.send(request, stream=True, follow_redirects=False, auth=None)
            response.raise_for_status()
            content = bytearray()
            async for chunk in response.aiter_bytes():
                if len(content) + len(chunk) > 2_000_000:
                    raise GitHubObservationError("GitHub job log exceeded its size limit")
                content.extend(chunk)
            return failure_log_excerpt(content.decode("utf-8", errors="replace"), max_chars)
        except httpx.HTTPStatusError as exc:
            raise github_http_error("job log", exc.response) from None
        except httpx.RequestError:
            raise GitHubObservationError("GitHub job log request failed") from None
        except httpx.InvalidURL:
            raise GitHubObservationError("GitHub job log returned an invalid download URL") from None
        finally:
            if response is not None:
                await response.aclose()

    async def current_login(self) -> str:
        user = await self._get("/user")
        login = user.get("login")
        if not isinstance(login, str) or not login:
            raise GitHubObservationError("GitHub returned an incomplete authenticated user")
        return login

    async def reconcile_issue_comment(
        self, repository: str, pull_number: int, marker: str, author: str
    ) -> dict[str, Any] | None:
        """Find one trusted marker using a bounded list of PR issue comments."""
        for page in range(1, 11):
            comments = await self._get_list(
                f"/repos/{repository}/issues/{pull_number}/comments", {"per_page": 100, "page": page}
            )
            for comment in comments:
                if comment.get("user", {}).get("login") == author and marker in str(comment.get("body") or ""):
                    return comment
            if len(comments) < 100:
                return None
        raise GitHubObservationError("GitHub comment reconciliation exceeded its pagination limit")

    async def list_issue_comments(self, repository: str, pull_number: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        for page in range(1, 11):
            batch = await self._get_list(
                f"/repos/{repository}/issues/{pull_number}/comments", {"per_page": 100, "page": page}
            )
            comments.extend(batch)
            if len(batch) < 100:
                return comments
        raise GitHubObservationError("GitHub comment observation exceeded its pagination limit")

    async def post_issue_comment(self, repository: str, pull_number: int, body: str) -> dict[str, Any]:
        try:
            response = await self.client.post(f"/repos/{repository}/issues/{pull_number}/comments", json={"body": body})
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise github_http_error("mention delivery", exc.response) from None
        except httpx.RequestError:
            raise GitHubObservationError("GitHub mention delivery request failed") from None
        try:
            value = response.json()
        except ValueError:
            raise GitHubObservationError("GitHub mention delivery returned invalid JSON") from None
        if not isinstance(value, dict):
            raise GitHubObservationError("GitHub mention delivery returned an invalid object")
        return value

    async def merge_pull_request(
        self, repository: str, pull_number: int, head_sha: str, merge_method: str = "squash"
    ) -> dict[str, Any]:
        """Ask GitHub to merge the exact head verified by Hub.

        GitHub remains the authority for branch protection and the actual merge
        result; callers must not treat a local CI observation as a merge.
        """
        try:
            response = await self.client.put(
                f"/repos/{repository}/pulls/{pull_number}/merge", json={"sha": head_sha, "merge_method": merge_method}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise github_http_error("merge", exc.response) from None
        except httpx.RequestError:
            raise GitHubObservationError("GitHub merge request failed") from None
        try:
            value = response.json()
        except ValueError:
            raise GitHubObservationError("GitHub merge returned invalid JSON") from None
        if not isinstance(value, dict):
            raise GitHubObservationError("GitHub merge returned an invalid object")
        return value

    async def find_pull_request(self, repository: str, head_branch: str) -> dict[str, Any] | None:
        owner = repository.split("/")[0]
        pulls = await self._get_list(f"/repos/{repository}/pulls", {"head": f"{owner}:{head_branch}", "state": "open"})
        if not pulls:
            pulls = await self._get_list(f"/repos/{repository}/pulls", {"head": head_branch, "state": "open"})
        return pulls[0] if pulls else None

    async def _list(self, path: str, key: str, params: dict[str, str | int]) -> list[dict[str, Any]]:
        items = []
        # Bounded pagination: incomplete observations fail instead of passing with partial evidence.
        for page in range(1, 11):
            data = await self._get(path, {**params, "per_page": 100, "page": page})
            batch = data.get(key)
            if not isinstance(batch, list) or any(not isinstance(item, dict) for item in batch):
                raise GitHubObservationError("GitHub observation returned an invalid list")
            items.extend(batch)
            if len(batch) < 100:
                total = data.get("total_count")
                if isinstance(total, int) and total > len(items):
                    raise GitHubObservationError("GitHub observation returned an incomplete page")
                return items
        raise GitHubObservationError("GitHub observation exceeded its pagination limit")

    async def observe_pull(self, config: PipelineObservationConfig, number: int) -> PullObservation:
        try:
            return await self._observe_pull(config, number)
        except (AttributeError, KeyError, TypeError, ValueError):
            raise GitHubObservationError("GitHub observation returned incomplete data") from None

    async def _observe_pull(self, config: PipelineObservationConfig, number: int) -> PullObservation:
        root = f"/repos/{config.repository}"
        pr_path = f"{root}/pulls/{number}"
        pr = await self._get(pr_path)
        head_sha = pr["head"]["sha"]
        observation = PullObservation(
            number=number,
            head_sha=head_sha,
            base_sha=pr["base"]["sha"],
            url=pr["html_url"],
            draft=pr.get("draft") is True,
            result=VerificationResult(status=VerificationStatus.WAITING, reason="Awaiting verification"),
        )
        if pr["state"] != "open":
            observation.result = VerificationResult(status=VerificationStatus.CLOSED, reason="PR is closed")
            return observation
        head_repo = (pr["head"].get("repo") or {}).get("full_name", "")
        if head_repo.lower() != config.repository.lower():
            observation.result = VerificationResult(
                status=VerificationStatus.BLOCKED, reason="Fork PRs are not supported in the initial observer"
            )
            return observation

        workflow = quote(config.verification.workflow, safe="")
        runs = await self._list(
            f"{root}/actions/workflows/{workflow}/runs",
            "workflow_runs",
            {"head_sha": head_sha, "event": config.verification.event},
        )
        candidates = [
            run
            for run in runs
            if run["head_sha"] == head_sha
            and run["event"] == config.verification.event
            and run["path"] == f".github/workflows/{config.verification.workflow}"
            and (run.get("head_repository") or {}).get("full_name", "").lower() == config.repository.lower()
            and any(
                pull["number"] == number and pull["head"]["sha"] == head_sha for pull in run.get("pull_requests", [])
            )
        ]
        if candidates:
            # Select the latest execution, never an older successful run while its replacement is pending.
            run = max(candidates, key=lambda item: (item["run_number"], item["id"]))
            verified_pull = next(pull for pull in run["pull_requests"] if pull["number"] == number)
            if (verified_pull.get("base") or {}).get("sha") != observation.base_sha:
                observation.result = VerificationResult(
                    status=VerificationStatus.WAITING,
                    reason="No workflow verification for the current PR base; run CI against the latest base",
                )
                return observation
            jobs = await self._list(f"{root}/actions/runs/{run['id']}/jobs", "jobs", {"filter": "latest"})
            observation.run = RunSnapshot(
                id=run["id"],
                attempt=run["run_attempt"],
                head_sha=run["head_sha"],
                status=run["status"],
                conclusion=run["conclusion"],
                url=run["html_url"],
                jobs=[
                    JobSnapshot(
                        id=job.get("id", 0),
                        name=job["name"],
                        status=job["status"],
                        conclusion=job["conclusion"],
                        url=job.get("html_url"),
                    )
                    for job in jobs
                ],
            )
            latest = await self._get(f"{root}/actions/runs/{run['id']}")
            if any(latest[key] != run[key] for key in ("run_attempt", "status", "conclusion", "updated_at")):
                observation.result = VerificationResult(
                    status=VerificationStatus.WAITING, reason="Workflow changed during observation; inspect again"
                )
                return observation

        current_pr = await self._get(pr_path)
        observation.draft = current_pr.get("draft") is True
        if (
            current_pr["head"]["sha"] != head_sha
            or current_pr["base"]["sha"] != pr["base"]["sha"]
            or current_pr["state"] != pr["state"]
        ):
            observation.result = VerificationResult(
                status=VerificationStatus.WAITING, reason="PR changed during observation; inspect again"
            )
            return observation
        mergeable_state = current_pr.get("mergeable_state")
        observation.mergeable_state = mergeable_state if isinstance(mergeable_state, str) else None
        observation.result = evaluate_verification(config.verification, head_sha, observation.run)
        return observation
