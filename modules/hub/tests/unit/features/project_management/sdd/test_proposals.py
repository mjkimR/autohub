import pytest
from app.features.project_management.sdd.proposals import proposal_state

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("status", ["draft", "reviewing", "accepted", "rejected", "unknown"])
def test_status_and_size_are_descriptive_not_activity_eligibility(status):
    text = f"---\nstatus: {status}\nsize: XL\nneeds_decompose: true\n---\n"
    row = proposal_state("demo", text, set(), {}, None)
    assert row["status"] == status
    assert row["actions"] == ["start_planning", "start_development"]
    assert "responsibility" in row["note"]


def test_active_run_is_an_owner_not_a_workflow_gate():
    row = proposal_state("demo", "---\nstatus: accepted\n---", set(), {}, {"id": "run"})
    assert row["actions"] == []


class _FakeGitHub:
    """Answers the proposal listing's GitHub reads from a path table and records them."""

    def __init__(self, responses):
        self.responses, self.calls = responses, []

    async def get(self, path, params=None):
        self.calls.append(path)
        value = self.responses.get(path)
        if isinstance(value, Exception):
            raise value
        return value


def _patch_github(monkeypatch, fake):
    from contextlib import asynccontextmanager

    from app.features.project_management.sdd import proposals

    class Work:
        def __init__(self, client):
            self.reader = self

        async def optional(self, path, params=None):
            return await fake.get(path, params)

        async def optional_list(self, path, params=None):
            return await fake.get(path, params)

        async def _get_list(self, path, params=None):
            return await fake.get(path, params) or []

    @asynccontextmanager
    async def client(token):
        yield None

    monkeypatch.setattr(proposals, "WorkGitHub", Work)
    monkeypatch.setattr(proposals.pipeline_services, "create_github_client", client)


async def test_proposals_come_from_one_tree_read_and_cached_anchors(monkeypatch):
    import base64
    from types import SimpleNamespace

    from app.features.project_management.repositories.services import BlobCache
    from app.features.project_management.sdd import proposals

    monkeypatch.setattr(proposals, "blob_cache", BlobCache())
    root = "/repos/o/r"
    anchor = base64.b64encode(b"---\ntitle: Demo\nstatus: draft\n---\n").decode()
    fake = _FakeGitHub(
        {
            f"{root}/git/ref/heads/main": {"object": {"sha": "base"}},
            f"{root}/git/trees/base": {
                "truncated": False,
                "tree": [
                    {"path": "docs/proposals", "type": "tree"},
                    {"path": "docs/proposals/PROP-demo", "type": "tree"},
                    {"path": "docs/proposals/PROP-demo/proposal.md", "type": "blob", "sha": "s1"},
                    {"path": "docs/proposals/PROP-empty", "type": "tree"},
                    {"path": "docs/proposals/README.md", "type": "blob", "sha": "s2"},
                ],
            },
            f"{root}/git/blobs/s1": {"encoding": "base64", "content": anchor, "size": 30},
            f"{root}/pulls": [{"number": 3, "head": {"ref": "plan-demo"}}],
        }
    )
    _patch_github(monkeypatch, fake)
    project = SimpleNamespace(github_connector_id="c", github_repository="o/r")
    observer = SimpleNamespace(get_token=lambda *_: _async("token"))

    async def runs_for(unit):
        return []

    first = await proposals.list_proposals(observer, project, "main", runs_for)
    assert [(i["slug"], i["title"], i["status"], i["plan_pull"]) for i in first["items"]] == [
        ("demo", "Demo", "draft", 3),
        ("empty", "PROP-empty", "unknown", None),
    ]
    assert first["truncated"] is False
    assert fake.calls.count(f"{root}/git/blobs/s1") == 1
    assert not any("/contents/" in call for call in fake.calls)

    fake.calls.clear()
    await proposals.list_proposals(observer, project, "main", runs_for)
    assert f"{root}/git/blobs/s1" not in fake.calls


async def test_a_truncated_tree_falls_back_to_directory_and_path_reads(monkeypatch):
    import base64
    from types import SimpleNamespace

    from app.features.project_management.sdd import proposals

    root = "/repos/o/r"
    anchor = base64.b64encode(b"---\ntitle: Demo\n---\n").decode()
    fake = _FakeGitHub(
        {
            f"{root}/git/ref/heads/main": {"object": {"sha": "base"}},
            f"{root}/git/trees/base": {"truncated": True, "tree": []},
            f"{root}/contents/docs/proposals": [{"name": "PROP-demo", "type": "dir"}],
            f"{root}/contents/docs/proposals/PROP-demo/proposal.md": {"encoding": "base64", "content": anchor},
        }
    )
    _patch_github(monkeypatch, fake)
    project = SimpleNamespace(github_connector_id="c", github_repository="o/r")
    observer = SimpleNamespace(get_token=lambda *_: _async("token"))

    async def runs_for(unit):
        return []

    listed = await proposals.list_proposals(observer, project, "main", runs_for)
    assert [i["title"] for i in listed["items"]] == ["Demo"]


async def _async(value):
    return value
