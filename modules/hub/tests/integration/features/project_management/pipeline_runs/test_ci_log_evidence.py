import httpx
import pytest

from tests.integration.features.project_management.pipeline_runs.test_merge_stage import (
    advance,
)
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import (
    github as github,
)
from tests.integration.features.project_management.pipeline_runs.test_merge_stage import (
    run as run,
)

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.mark.parametrize("log_status", [200, 403])
async def test_ci_fix_uses_failure_context_and_log_access_is_best_effort(client, run, github, monkeypatch, log_status):
    github.ci_conclusion = "failure"
    original = github.respond
    log = "2026-09-22T00:12:13.1610300Z AssertionError: expected 5, got 11 token=test-secret\n"
    log += "2026-09-22T00:12:13.1625030Z ##[error]Process completed with exit code 1.\n"
    log += "2026-09-22T00:12:13.3500323Z [command]git config cleanup\n" * 100

    def respond(request):
        if request.url.path.endswith("/actions/jobs/1/logs"):
            return httpx.Response(log_status, text=log)
        return original(request)

    monkeypatch.setattr(github, "respond", respond)
    advanced = await advance(client, run)
    assert advanced["state"] == "dispatching"
    attempts = (await client.get(f"/api/v1/pipeline-runs/{run['id']}/attempts")).json()["items"]
    fix = next(attempt for attempt in attempts if attempt["kind"] == "ci-fix")
    instructions = fix["request_snapshot"]["instructions"]
    assert "Fix these jobs: lint" in instructions
    assert "test-secret" not in instructions
    assert "git config cleanup" not in instructions
    if log_status == 200:
        assert "AssertionError: expected 5, got 11 [REDACTED]" in instructions
    else:
        assert "Bounded failing-job log excerpt" not in instructions
