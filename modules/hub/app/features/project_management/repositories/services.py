import base64
from typing import Any

import httpx
from app.features.project_management.pipelines.github import (
    GitHubObservationError,
    create_github_client,
    github_http_error,
)
from app.features.project_management.repositories.schemas import (
    RepoBlobRead,
    RepoInfoRead,
    RepoItemRead,
    RepoTreeRead,
)


class RepositoryService:
    async def get_info(self, token: str, repository: str) -> RepoInfoRead:
        async with create_github_client(token) as client:
            repo_data = await self._get(client, f"/repos/{repository}")
            default_branch = repo_data.get("default_branch", "main")
            try:
                branches_data = await self._get(client, f"/repos/{repository}/branches", params={"per_page": 100})
                branches = [b["name"] for b in branches_data if isinstance(b, dict) and "name" in b]
            except Exception:
                branches = [default_branch]
            if default_branch not in branches:
                branches.insert(0, default_branch)
            return RepoInfoRead(
                repository=repository,
                default_branch=default_branch,
                branches=branches,
            )

    async def get_tree(self, token: str, repository: str, path: str = "", ref: str = "") -> RepoTreeRead:
        clean_path = path.strip("/")
        endpoint = f"/repos/{repository}/contents/{clean_path}" if clean_path else f"/repos/{repository}/contents"
        params: dict[str, str | int] = {}
        if ref:
            params["ref"] = ref

        async with create_github_client(token) as client:
            data = await self._get(client, endpoint, params=params)

        if not isinstance(data, list):
            # If a file path was passed to tree, wrap it or return error
            if isinstance(data, dict) and data.get("type") == "file":
                item = RepoItemRead(
                    name=data.get("name", ""),
                    path=data.get("path", clean_path),
                    type="file",
                    size=data.get("size", 0),
                    sha=data.get("sha", ""),
                )
                return RepoTreeRead(path=clean_path, ref=ref, items=[item])
            raise GitHubObservationError(f"Path '{clean_path}' is not a directory", 400)

        items: list[RepoItemRead] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            kind = entry.get("type")
            if kind not in ("file", "dir"):
                continue
            items.append(
                RepoItemRead(
                    name=entry.get("name", ""),
                    path=entry.get("path", ""),
                    type="dir" if kind == "dir" else "file",
                    size=entry.get("size", 0),
                    sha=entry.get("sha", ""),
                )
            )

        # Sort: directories first (alphabetical), then files (alphabetical)
        items.sort(key=lambda x: (0 if x.type == "dir" else 1, x.name.lower()))
        return RepoTreeRead(path=clean_path, ref=ref, items=items)

    async def get_blob(self, token: str, repository: str, path: str, ref: str = "") -> RepoBlobRead:
        clean_path = path.strip("/")
        endpoint = f"/repos/{repository}/contents/{clean_path}"
        params: dict[str, str | int] = {}
        if ref:
            params["ref"] = ref

        async with create_github_client(token) as client:
            data = await self._get(client, endpoint, params=params)

        if not isinstance(data, dict) or data.get("type") != "file":
            raise GitHubObservationError(f"Path '{clean_path}' is not a file", 400)

        raw_content = data.get("content", "")
        # GitHub base64 content often has newlines
        clean_b64 = raw_content.replace("\n", "").replace("\r", "")
        try:
            decoded_bytes = base64.b64decode(clean_b64.encode("ascii"))
            content_str = decoded_bytes.decode("utf-8")
            encoding = "utf-8"
        except (ValueError, UnicodeDecodeError):
            content_str = clean_b64
            encoding = "base64"

        return RepoBlobRead(
            path=clean_path,
            ref=ref,
            size=data.get("size", 0),
            sha=data.get("sha", ""),
            encoding=encoding,
            content=content_str,
        )

    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, str | int] | None = None,
    ) -> Any:
        try:
            response = await client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise github_http_error("repository browsing", exc.response) from None
        except httpx.RequestError:
            raise GitHubObservationError("GitHub repository request failed") from None
        try:
            return response.json()
        except ValueError:
            raise GitHubObservationError("Invalid JSON in GitHub response") from None
