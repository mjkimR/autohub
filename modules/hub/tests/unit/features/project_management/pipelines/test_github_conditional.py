import httpx2
import pytest
from app.features.project_management.pipelines import github
from app.features.project_management.pipelines.conditional import ConditionalCache
from app.features.project_management.pipelines.github import GitHubActionsReader, GitHubObservationError

pytestmark = pytest.mark.unit


def _reader(monkeypatch, replies):
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return replies.pop(0)

    monkeypatch.setattr(github, "observation_cache", ConditionalCache())
    client = httpx2.AsyncClient(base_url="https://api.github.com", transport=httpx2.MockTransport(handle))
    return GitHubActionsReader(client), requests


async def test_observation_reads_revalidate_with_etags(monkeypatch):
    pull = {"number": 1, "draft": True}
    reader, requests = _reader(
        monkeypatch,
        [
            httpx2.Response(200, json=pull, headers={"ETag": '"v1"'}),
            httpx2.Response(304, headers={"ETag": '"v1"'}),
            httpx2.Response(200, json={**pull, "draft": False}, headers={"ETag": '"v2"'}),
            httpx2.Response(200, json=[{"id": 1}], headers={"ETag": 'W/"list"'}),
            httpx2.Response(304),
        ],
    )
    assert await reader._get("/repos/o/r/pulls/1") == pull
    assert await reader._get("/repos/o/r/pulls/1") == pull
    assert requests[1].headers["if-none-match"] == '"v1"'
    assert (await reader._get("/repos/o/r/pulls/1"))["draft"] is False
    assert requests[2].headers["if-none-match"] == '"v1"'
    assert await reader._get_list("/repos/o/r/pulls", {"state": "open"}) == [{"id": 1}]
    assert "if-none-match" not in requests[3].headers
    assert await reader._get_list("/repos/o/r/pulls", {"state": "open"}) == [{"id": 1}]
    assert requests[4].headers["if-none-match"] == 'W/"list"'


async def test_observation_errors_are_not_cached_and_unsolicited_not_modified_fails(monkeypatch):
    reader, requests = _reader(
        monkeypatch,
        [
            httpx2.Response(404, json={"message": "Not Found"}, headers={"ETag": '"e"'}),
            httpx2.Response(304),
        ],
    )
    with pytest.raises(GitHubObservationError):
        await reader._get("/repos/o/r/pulls/2")
    assert not github.observation_cache.entries
    with pytest.raises(GitHubObservationError):
        await reader._get("/repos/o/r/pulls/2")
    assert "if-none-match" not in requests[1].headers
