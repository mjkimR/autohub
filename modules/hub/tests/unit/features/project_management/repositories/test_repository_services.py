import base64

from app.features.project_management.repositories.schemas import (
    RepoBlobRead,
    RepoInfoRead,
    RepoItemRead,
)


def test_repo_item_schema():
    item = RepoItemRead(name="README.md", path="README.md", type="file", size=1024, sha="abc123")
    assert item.name == "README.md"
    assert item.type == "file"
    assert item.size == 1024


def test_repo_tree_sorting():
    items = [
        RepoItemRead(name="zebra.txt", path="zebra.txt", type="file", size=10, sha="1"),
        RepoItemRead(name="docs", path="docs", type="dir", size=0, sha="2"),
        RepoItemRead(name="alpha.txt", path="alpha.txt", type="file", size=20, sha="3"),
        RepoItemRead(name="architecture", path="architecture", type="dir", size=0, sha="4"),
    ]
    # Sort matching RepositoryService logic: dirs first, then files, case-insensitive
    items.sort(key=lambda x: (0 if x.type == "dir" else 1, x.name.lower()))
    assert [x.name for x in items] == ["architecture", "docs", "alpha.txt", "zebra.txt"]


def test_repo_blob_utf8_decode():
    content = "# Hello World\nLiving Spec"
    b64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")

    # Simulate blob processing logic
    clean_b64 = b64_content.replace("\n", "")
    decoded = base64.b64decode(clean_b64.encode("ascii")).decode("utf-8")

    blob = RepoBlobRead(
        path="docs/README.md",
        ref="main",
        size=len(content),
        sha="blobsha",
        encoding="utf-8",
        content=decoded,
    )
    assert blob.encoding == "utf-8"
    assert blob.content == content


def test_repo_info_schema():
    info = RepoInfoRead(
        repository="owner/repo",
        default_branch="main",
        branches=["main", "feature/1"],
    )
    assert info.repository == "owner/repo"
    assert info.default_branch == "main"
    assert len(info.branches) == 2


async def test_branch_listing_reads_later_pages_and_reports_incomplete_results(monkeypatch):
    from unittest.mock import AsyncMock

    from app.features.project_management.pipelines.github import GitHubObservationError
    from app.features.project_management.repositories.services import RepositoryService

    service = RepositoryService()
    first = [{"name": f"branch-{i}"} for i in range(100)]
    get = AsyncMock(side_effect=[{"default_branch": "main"}, first, [{"name": "dev-late"}]])
    monkeypatch.setattr(service, "_get", get)
    info = await service.get_info("token", "owner/repo")
    assert info.branches_complete
    assert info.branches[-1] == "dev-late"
    assert get.call_args.kwargs["params"]["page"] == 2

    get.side_effect = [{"default_branch": "main"}, first, GitHubObservationError("rate limit", 429)]
    info = await service.get_info("token", "owner/repo")
    assert not info.branches_complete
    assert info.branches[0] == "main"


async def test_whole_tree_listing_maps_entries_and_reports_truncation(monkeypatch):
    from unittest.mock import AsyncMock

    from app.features.project_management.repositories import services
    from app.features.project_management.repositories.services import RepositoryService

    service = RepositoryService()
    tree = [
        {"path": "docs", "type": "tree", "mode": "040000", "sha": "t1"},
        {"path": "docs/a.md", "type": "blob", "mode": "100644", "sha": "b1", "size": 12},
        {"path": "docs/link", "type": "blob", "mode": "120000", "sha": "b2", "size": 5},
        {"path": "vendor/lib", "type": "commit", "mode": "160000", "sha": "c1"},
    ]
    get = AsyncMock(return_value={"sha": "root", "truncated": False, "tree": tree})
    monkeypatch.setattr(service, "_get", get)
    listing = await service.get_paths("token", "owner/repo", ref="autohub/work/x")
    assert get.call_args.args[1] == "/repos/owner/repo/git/trees/autohub/work/x"
    assert get.call_args.kwargs["params"] == {"recursive": 1}
    assert [(i.path, i.name, i.type, i.size) for i in listing.items] == [
        ("docs", "docs", "dir", 0),
        ("docs/a.md", "a.md", "file", 12),
    ]
    assert not listing.truncated

    await service.get_paths("token", "owner/repo")
    assert get.call_args.args[1] == "/repos/owner/repo/git/trees/HEAD"

    get.return_value = {"sha": "root", "truncated": True, "tree": tree}
    assert (await service.get_paths("token", "owner/repo")).model_dump()["truncated"] is True
    monkeypatch.setattr(services, "PATHS_LIMIT", 1)
    get.return_value = {"sha": "root", "truncated": False, "tree": tree}
    cut = await service.get_paths("token", "owner/repo")
    assert cut.truncated and cut.items == []


async def test_blob_read_with_a_known_sha_reuses_cached_content(monkeypatch):
    from unittest.mock import AsyncMock

    from app.features.project_management.repositories import services
    from app.features.project_management.repositories.services import BlobCache, RepositoryService

    monkeypatch.setattr(services, "blob_cache", BlobCache())
    service = RepositoryService()
    sha = "a" * 40
    body = {"type": "file", "size": 5, "sha": sha, "content": base64.b64encode(b"hello").decode()}
    get = AsyncMock(return_value=body)
    monkeypatch.setattr(service, "_get", get)

    first = await service.get_blob("token", "Owner/Repo", "docs/a.md", ref="main", sha=sha)
    again = await service.get_blob("token", "owner/repo", "/docs/a.md", ref="main", sha=sha)
    assert get.await_count == 1
    assert (
        again.model_dump()
        == first.model_dump()
        == {
            "path": "docs/a.md",
            "ref": "main",
            "size": 5,
            "sha": sha,
            "encoding": "utf-8",
            "content": "hello",
        }
    )
    # Without a SHA the read always goes to GitHub; another repository never shares the entry.
    await service.get_blob("token", "owner/repo", "docs/a.md", ref="main")
    await service.get_blob("token", "other/repo", "docs/a.md", ref="main", sha=sha)
    assert get.await_count == 3

    # Files past GitHub's inline limit are never cached.
    big = "b" * 40
    get.return_value = {**body, "sha": big, "size": services.INLINE_BLOB_LIMIT + 1}
    await service.get_blob("token", "owner/repo", "big.bin", sha=big)
    await service.get_blob("token", "owner/repo", "big.bin", sha=big)
    assert get.await_count == 5


def test_blob_cache_evicts_least_recently_used_within_its_byte_budget():
    from app.features.project_management.repositories.services import BlobCache

    cache = BlobCache(max_bytes=10)
    cache.put("o/r", "1", 4, "utf-8", "aaaa")
    cache.put("o/r", "2", 4, "utf-8", "bbbb")
    assert cache.get("o/r", "1")  # 1 becomes the most recent
    cache.put("o/r", "3", 4, "utf-8", "cccc")
    assert cache.get("o/r", "2") is None
    assert cache.get("o/r", "1") and cache.get("o/r", "3")
    assert cache.bytes == 8
    cache.put("o/r", "4", 11, "utf-8", "d" * 11)
    assert cache.get("o/r", "4") is None


def _github(monkeypatch, respond):
    """Route the service's GitHub client through ``respond`` and give it a fresh conditional cache."""
    import httpx2
    from app.features.project_management.repositories import services
    from app.features.project_management.repositories.conditional import ConditionalCache

    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return respond(request)

    monkeypatch.setattr(services, "conditional_cache", ConditionalCache())
    monkeypatch.setattr(
        services,
        "create_github_client",
        lambda token: httpx2.AsyncClient(base_url="https://api.github.com", transport=httpx2.MockTransport(handle)),
    )
    return requests


async def test_repository_reads_revalidate_with_etags_and_reuse_bodies_on_not_modified(monkeypatch):
    import httpx2
    from app.features.project_management.repositories import services
    from app.features.project_management.repositories.services import RepositoryService

    tree = {"sha": "root", "truncated": False, "tree": [{"path": "a.md", "type": "blob", "mode": "100644", "sha": "b"}]}
    replies = [
        httpx2.Response(200, json=tree, headers={"ETag": '"v1"'}),
        httpx2.Response(304, headers={"ETag": '"v1"'}),
        httpx2.Response(200, json={**tree, "sha": "root2"}, headers={"ETag": '"v2"'}),
        httpx2.Response(304, headers={"ETag": '"v2"'}),
    ]
    requests = _github(monkeypatch, lambda request: replies.pop(0))
    service = RepositoryService()

    first = await service.get_paths("token", "owner/repo", ref="main")
    assert "if-none-match" not in requests[0].headers
    held = services.conditional_cache.get(("/repos/owner/repo/git/trees/main", (("recursive", "1"),)))
    assert held and held[0] == '"v1"'

    unchanged = await service.get_paths("token", "owner/repo", ref="main")
    assert requests[1].headers["if-none-match"] == '"v1"'
    assert unchanged.model_dump() == first.model_dump()

    changed = await service.get_paths("token", "owner/repo", ref="main")
    assert requests[2].headers["if-none-match"] == '"v1"'
    assert changed.sha == "root2"

    again = await service.get_paths("token", "owner/repo", ref="main")
    assert requests[3].headers["if-none-match"] == '"v2"'
    assert again.sha == "root2"
    # Other parameters are another request: no validator is sent for them.
    replies.append(httpx2.Response(200, json=tree))
    await service.get_paths("token", "owner/repo", ref="dev")
    assert "if-none-match" not in requests[4].headers


async def test_repository_read_errors_are_never_cached_and_keep_their_classification(monkeypatch):
    import httpx2
    import pytest
    from app.features.project_management.pipelines.github import GITHUB_FAILURE_RATE_LIMITED, GitHubObservationError
    from app.features.project_management.repositories import services
    from app.features.project_management.repositories.services import RepositoryService

    file = {"type": "file", "size": 5, "sha": "s", "content": base64.b64encode(b"hello").decode()}
    replies = [
        httpx2.Response(404, json={"message": "Not Found"}, headers={"ETag": '"e404"'}),
        httpx2.Response(403, headers={"x-ratelimit-remaining": "0", "ETag": '"e403"'}),
        httpx2.Response(200, json=file, headers={"ETag": '"v1"'}),
        httpx2.Response(404, json={"message": "Not Found"}),
        httpx2.Response(304),
    ]
    requests = _github(monkeypatch, lambda request: replies.pop(0))
    service = RepositoryService()

    with pytest.raises(GitHubObservationError) as missing:
        await service.get_blob("token", "owner/repo", "a.md")
    assert missing.value.status_code == 404
    with pytest.raises(GitHubObservationError) as limited:
        await service.get_blob("token", "owner/repo", "a.md")
    assert limited.value.kind == GITHUB_FAILURE_RATE_LIMITED
    assert "if-none-match" not in requests[1].headers and not services.conditional_cache.entries

    assert (await service.get_blob("token", "owner/repo", "a.md")).content == "hello"
    # A caller GitHub refuses gets its own error even though a body is held for the same URL.
    with pytest.raises(GitHubObservationError) as denied:
        await service.get_blob("other-token", "owner/repo", "a.md")
    assert requests[3].headers["if-none-match"] == '"v1"'
    assert denied.value.status_code == 404
    held = services.conditional_cache.get(("/repos/owner/repo/contents/a.md", ()))
    assert held and held[0] == '"v1"'
    assert (await service.get_blob("token", "owner/repo", "a.md")).content == "hello"


async def test_unsolicited_not_modified_is_an_error(monkeypatch):
    import httpx2
    import pytest
    from app.features.project_management.pipelines.github import GitHubObservationError
    from app.features.project_management.repositories.services import RepositoryService

    _github(monkeypatch, lambda request: httpx2.Response(304))
    with pytest.raises(GitHubObservationError) as exc:
        await RepositoryService().get_tree("token", "owner/repo")
    assert exc.value.status_code == 304


def test_conditional_cache_evicts_least_recently_used_within_its_bounds():
    from app.features.project_management.repositories.conditional import ConditionalCache, conditional_key

    cache = ConditionalCache(max_entries=3, max_bytes=10, max_entry_bytes=6)
    a, b, c, d = (conditional_key(f"/{n}", {"page": 1}) for n in "abcd")
    assert conditional_key("/a", {"z": 1, "a": "x"}) == ("/a", (("a", "x"), ("z", "1")))
    cache.put(a, '"a"', b"aaaa")
    cache.put(b, '"b"', b"bbbb")
    assert cache.get(a)  # a becomes the most recent
    cache.put(c, '"c"', b"cc")
    cache.put(d, '"d"', b"dd")  # over the byte budget: b goes first
    assert cache.get(b) is None and cache.get(a) and cache.get(c) and cache.get(d)
    assert cache.bytes == 8

    small = ConditionalCache(max_entries=2)
    for key in (a, b, c):
        small.put(key, '"x"', b"x")
    assert list(small.entries) == [b, c]

    cache.put(a, '"a2"', b"aaaaaaa")  # oversized body: not stored, stale entry dropped
    assert cache.get(a) is None and cache.bytes == 4
    cache.put(c, "", b"c")  # no ETag: nothing to revalidate
    assert cache.get(c) is None
