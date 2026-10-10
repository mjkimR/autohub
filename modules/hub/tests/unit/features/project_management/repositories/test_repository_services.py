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
