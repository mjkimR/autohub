import base64
from collections import OrderedDict
from typing import Any, Literal
from urllib.parse import quote

import httpx2
from app.features.project_management.pipelines.github import (
    GitHubObservationError,
    create_github_client,
    github_http_error,
)
from app.features.project_management.repositories.schemas import (
    RepoBlobRead,
    RepoInfoRead,
    RepoItemRead,
    RepoPathsRead,
    RepoTreeRead,
)

# A whole-tree listing larger than this is reported as truncated; callers list directories instead.
PATHS_LIMIT = 20_000
# GitHub's contents API inlines files up to 1 MiB; larger blobs keep that read path.
INLINE_BLOB_LIMIT = 1024 * 1024


Encoding = Literal["utf-8", "base64"]


class BlobCache:
    """Decoded file content by repository and Git blob SHA.

    A blob SHA names immutable content, so entries never go stale; the cache only bounds memory
    (least recently used first). It never stores a read that failed or exceeded the inline limit.
    """

    def __init__(self, max_bytes: int = 32 * 1024 * 1024):
        self.max_bytes = max_bytes
        self.bytes = 0
        self.entries: OrderedDict[tuple[str, str], tuple[int, Encoding, str]] = OrderedDict()

    def get(self, repository: str, sha: str) -> tuple[int, Encoding, str] | None:
        key = (repository.lower(), sha)
        entry = self.entries.get(key)
        if entry is not None:
            self.entries.move_to_end(key)
        return entry

    def put(self, repository: str, sha: str, size: int, encoding: Encoding, content: str) -> None:
        key = (repository.lower(), sha)
        cost = len(content)
        if not sha or cost > self.max_bytes or key in self.entries:
            return
        self.entries[key] = (size, encoding, content)
        self.bytes += cost
        while self.bytes > self.max_bytes:
            _, (_, _, dropped) = self.entries.popitem(last=False)
            self.bytes -= len(dropped)


blob_cache = BlobCache()


def _decode(raw_content: str) -> tuple[str, Encoding]:
    # GitHub base64 content often has newlines
    clean_b64 = raw_content.replace("\n", "").replace("\r", "")
    try:
        return base64.b64decode(clean_b64.encode("ascii")).decode("utf-8"), "utf-8"
    except (ValueError, UnicodeDecodeError):
        return clean_b64, "base64"


class RepositoryService:
    async def get_info(self, token: str, repository: str) -> RepoInfoRead:
        async with create_github_client(token) as client:
            repo_data = await self._get(client, f"/repos/{repository}")
            default_branch = repo_data.get("default_branch", "main")
            branches: list[str] = []
            complete = False
            try:
                for page in range(1, 11):
                    rows = await self._get(
                        client, f"/repos/{repository}/branches", params={"per_page": 100, "page": page}
                    )
                    if not isinstance(rows, list):
                        raise GitHubObservationError("Invalid GitHub branch list")
                    branches.extend(b["name"] for b in rows if isinstance(b, dict) and isinstance(b.get("name"), str))
                    if len(rows) < 100:
                        complete = True
                        break
            except GitHubObservationError:
                pass  # the Git browser remains usable; roadmap must disclose incomplete branch coverage
            if default_branch not in branches:
                branches.insert(0, default_branch)
            return RepoInfoRead(
                repository=repository,
                default_branch=default_branch,
                branches=list(dict.fromkeys(branches)),
                branches_complete=complete,
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

    async def get_paths(self, token: str, repository: str, ref: str = "") -> RepoPathsRead:
        """Every path of the ref's tree in one GitHub request, for directory listings without one request each."""
        endpoint = f"/repos/{repository}/git/trees/{quote(ref or 'HEAD', safe='/')}"
        async with create_github_client(token) as client:
            data = await self._get(client, endpoint, params={"recursive": 1})
        entries = data.get("tree") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            raise GitHubObservationError("Invalid GitHub tree listing")
        truncated = bool(data.get("truncated")) or len(entries) > PATHS_LIMIT
        if truncated:
            return RepoPathsRead(ref=ref, sha=str(data.get("sha", "")), truncated=True)
        items: list[RepoItemRead] = []
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                continue
            kind, mode = entry.get("type"), entry.get("mode")
            # Symbolic links (mode 120000) and submodules ("commit") are not browsable, as in directory listings.
            if kind == "tree":
                item_type = "dir"
            elif kind == "blob" and mode != "120000":
                item_type = "file"
            else:
                continue
            path = entry["path"]
            items.append(
                RepoItemRead(
                    name=path.rsplit("/", 1)[-1],
                    path=path,
                    type=item_type,
                    size=entry.get("size", 0) if item_type == "file" else 0,
                    sha=entry.get("sha", ""),
                )
            )
        return RepoPathsRead(ref=ref, sha=str(data.get("sha", "")), items=items)

    async def get_blob(self, token: str, repository: str, path: str, ref: str = "", sha: str = "") -> RepoBlobRead:
        """File content at ``path``; a known blob ``sha`` (from a listing) is served from the cache when held."""
        clean_path = path.strip("/")
        if sha and (cached := blob_cache.get(repository, sha)):
            size, encoding, content = cached
            return RepoBlobRead(path=clean_path, ref=ref, size=size, sha=sha, encoding=encoding, content=content)
        endpoint = f"/repos/{repository}/contents/{clean_path}"
        params: dict[str, str | int] = {}
        if ref:
            params["ref"] = ref

        async with create_github_client(token) as client:
            data = await self._get(client, endpoint, params=params)

        if not isinstance(data, dict) or data.get("type") != "file":
            raise GitHubObservationError(f"Path '{clean_path}' is not a file", 400)

        size = data.get("size", 0)
        content_str, encoding = _decode(data.get("content", ""))
        blob_sha = data.get("sha", "")
        if size <= INLINE_BLOB_LIMIT:
            blob_cache.put(repository, blob_sha, size, encoding, content_str)
        return RepoBlobRead(
            path=clean_path,
            ref=ref,
            size=size,
            sha=blob_sha,
            encoding=encoding,
            content=content_str,
        )

    async def _get(
        self,
        client: httpx2.AsyncClient,
        path: str,
        params: dict[str, str | int] | None = None,
    ) -> Any:
        try:
            response = await client.get(path, params=params)
            response.raise_for_status()
        except httpx2.HTTPStatusError as exc:
            raise github_http_error("repository browsing", exc.response) from None
        except httpx2.RequestError:
            raise GitHubObservationError("GitHub repository request failed") from None
        try:
            return response.json()
        except ValueError:
            raise GitHubObservationError("Invalid JSON in GitHub response") from None
