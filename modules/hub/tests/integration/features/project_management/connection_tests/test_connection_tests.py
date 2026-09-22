import base64
import json
from copy import deepcopy
from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from app.features.execution.tasks.domains.pipeline import connection_probe
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.connection_tests.repos import ConnectionTestRepository
from app.features.project_management.pipelines import services
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from app_testing_base import utc_now
from sqlalchemy import select, update

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_scheduler_advances_probe_without_an_open_page(
    client, project, github, monkeypatch, credential_key_provider
):
    monkeypatch.setattr(connection_probe, "get_credential_key_provider", lambda: credential_key_provider)
    test = await start(client, project)
    response = await client.post("/api/v1/dispatchers/trigger")
    assert response.status_code == 200, response.text
    history = await client.get(f"/api/v1/projects/{project['id']}/connection-tests")
    assert history.json()[0]["id"] == test["id"]
    assert history.json()[0]["phase"] == "dispatching"
    assert github.pr is not None and github.pr["draft"]


class ProbeGitHub:
    def __init__(self):
        self.branch = None
        self.pr = None
        self.content = None
        self.head = "a" * 40
        self.comments = []
        self.writes = []
        self.lose_comment_response = False
        self.fail_cleanup = False
        self.ci = "success"

    def respond(self, request):
        path, method = request.url.path, request.method
        body = json.loads(request.content) if request.content else {}
        if method != "GET":
            self.writes.append((method, path, body))
        assert not path.endswith("/merge"), "A connection test must never invoke GitHub merge"
        if path == "/user":
            return httpx.Response(200, json={"login": "owner", "type": "User"})
        if path == "/repos/owner/app":
            return httpx.Response(200, json={"default_branch": "main", "full_name": "owner/app"})
        if "/labels" in path:
            if "/issues/" in path and self.pr:
                self.pr["labels"] = [{"name": label} for label in body["labels"]]
            return httpx.Response(200, json={"name": "autohub-connection-test"})
        if "/git/ref/heads/" in path:
            if path.endswith("/main") or self.branch:
                return httpx.Response(200, json={"object": {"sha": self.head}})
            return httpx.Response(404)
        if path.endswith("/git/refs") and method == "POST":
            self.branch = body["ref"].removeprefix("refs/heads/")
            return httpx.Response(201, json={})
        if "/contents/" in path:
            if method == "PUT":
                self.content = body["content"]
                return httpx.Response(201, json={})
            return (
                httpx.Response(200, json={"encoding": "base64", "content": self.content})
                if self.content
                else httpx.Response(404)
            )
        if path.endswith("/pulls"):
            if method == "POST":
                assert body["draft"] is True
                self.pr = {
                    "number": 42,
                    "title": body["title"],
                    "body": body["body"],
                    "draft": True,
                    "state": "open",
                    "head": {"ref": self.branch, "sha": self.head, "repo": {"full_name": "owner/app"}},
                    "base": {"ref": "main", "sha": "b" * 40},
                    "html_url": "https://github.com/owner/app/pull/42",
                }
                return httpx.Response(201, json=self.pr)
            return httpx.Response(200, json=[self.pr] if self.pr else [])
        if path.endswith("/pulls/42"):
            assert self.pr is not None
            if method == "PATCH":
                if self.fail_cleanup:
                    return httpx.Response(503)
                self.pr.update(body)
            return httpx.Response(200, json=deepcopy(self.pr))
        if path.endswith("/comments"):
            if method == "POST":
                comment = {
                    "id": len(self.comments) + 1,
                    "body": body["body"],
                    "user": {"login": "owner"},
                    "html_url": "https://github.com/owner/app/pull/42#issuecomment-1",
                }
                self.comments.append(comment)
                if self.lose_comment_response:
                    self.lose_comment_response = False
                    raise httpx.ReadTimeout("response lost", request=request)
                return httpx.Response(201, json=comment)
            return httpx.Response(200, json=self.comments)
        run = {
            "id": 10,
            "run_number": 1,
            "run_attempt": 1,
            "head_sha": self.head,
            "event": "pull_request",
            "path": ".github/workflows/ci.yml",
            "head_repository": {"full_name": "owner/app"},
            "pull_requests": [{"number": 42, "head": {"sha": self.head}, "base": {"sha": "b" * 40}}],
            "status": "completed",
            "conclusion": self.ci,
            "html_url": "https://github.com/owner/app/actions/runs/10",
            "updated_at": "2026-09-22T00:00:00Z",
        }
        if path.endswith("/actions/workflows/ci.yml/runs"):
            return httpx.Response(200, json={"workflow_runs": [run]})
        if path.endswith("/actions/runs/10/jobs"):
            return httpx.Response(200, json={"jobs": [{"name": "test", "status": "completed", "conclusion": self.ci}]})
        if path.endswith("/actions/runs/10"):
            return httpx.Response(200, json=run)
        if "/git/refs/heads/" in path and method == "DELETE":
            self.branch = None
            return httpx.Response(204)
        raise AssertionError(f"Unexpected {method} {path}")

    def push(self, test_id, correct=True):
        assert self.pr is not None
        self.head = "c" * 40
        self.pr["head"]["sha"] = self.head
        self.content = base64.b64encode(f"{'verified' if correct else 'wrong'}:{test_id}\n".encode()).decode()


@pytest.fixture
def github(monkeypatch):
    scenario = ProbeGitHub()
    monkeypatch.setattr(
        services,
        "create_github_client",
        lambda token: httpx.AsyncClient(
            base_url="https://api.github.com", transport=httpx.MockTransport(scenario.respond)
        ),
    )
    return scenario


@pytest.fixture
async def project(client, github):
    connector = await client.post(
        "/api/v1/connectors", json={"name": "probe", "provider": "github", "credentials": {"token": "test-token"}}
    )
    assert connector.status_code == 201
    result = await client.post(
        "/api/v1/projects",
        json={
            "name": "Probe project",
            "github": {
                "repository": "owner/app",
                "github_connector_id": connector.json()["id"],
                "verification": {"workflow": "ci.yml", "required_jobs": ["test"]},
                "automation": {"auto_merge": True},
            },
        },
    )
    assert result.status_code == 201
    return result.json()


async def start(client, project, request_id=None):
    result = await client.post(
        f"/api/v1/projects/{project['id']}/connection-tests", json={"request_id": request_id or str(uuid4())}
    )
    assert result.status_code == 201, result.text
    return result.json()


async def step(client, test, action="advance"):
    result = await client.post(f"/api/v1/projects/{test['project_id']}/connection-tests/{test['id']}/{action}")
    assert result.status_code == 200, result.text
    return result.json()


async def test_success_never_merges_and_preserves_result_when_cleanup_retries(client, project, github):
    test = await start(client, project)
    test = await step(client, test)
    assert test["phase"] == "dispatching"
    test = await step(client, test)
    assert test["phase"] == "waiting_for_push"
    github.push(test["id"])
    # Even a human making the probe ready must not enable the project's default automatic merge.
    github.pr["draft"] = False
    test = await step(client, test)
    assert test["status"] == "succeeded"
    assert test["evidence"]["verified_sha"] == github.head
    github.fail_cleanup = True
    test = await step(client, test)
    assert test["status"] == "succeeded" and test["cleanup_status"] == "failed"
    github.fail_cleanup = False
    test = await step(client, test)
    assert test["status"] == "succeeded" and test["cleanup_status"] == "completed"
    assert github.pr["state"] == "closed" and github.branch is None
    assert (await client.delete(f"/api/v1/projects/{project['id']}")).status_code == 409


async def test_idempotent_start_and_uncertain_mention_reconcile(client, project, github):
    test = await start(client, project)
    assert (await start(client, project, test["id"]))["id"] == test["id"]
    conflict = await client.post(
        f"/api/v1/projects/{project['id']}/connection-tests", json={"request_id": str(uuid4())}
    )
    assert conflict.status_code == 409
    test = await step(client, test)
    github.lose_comment_response = True
    test = await step(client, test)
    assert test["phase"] == "dispatching"
    test = await step(client, test)
    assert test["phase"] == "waiting_for_push" and len(github.comments) == 1


@pytest.mark.parametrize("implemented", [True, False])
async def test_probe_cannot_be_enrolled_even_after_completion(client, project, github, implemented):
    test = await step(client, await start(client, project))
    response = await client.post(
        f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 42, "implemented": implemented}
    )
    assert response.status_code == 422
    await step(client, test, "cancel")
    response = await client.post(
        f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 42, "implemented": implemented}
    )
    assert response.status_code == 422


async def test_wrong_marker_and_skipped_ci_do_not_verify(client, project, github):
    test = await step(client, await start(client, project))
    test = await step(client, test)
    github.push(test["id"], correct=False)
    test = await step(client, test)
    assert test["status"] == "running" and "verified_sha" not in test["evidence"]
    github.push(test["id"])
    github.ci = "skipped"
    test = await step(client, test)
    assert test["status"] == "running" and test["evidence"]["ci_status"] == "blocked"


@pytest.mark.parametrize("cancel", [True, False])
async def test_cancel_or_deadline_closes_pr_and_delays_branch_cleanup(client, project, github, session, cancel):
    test = await step(client, await start(client, project))
    test = await step(client, test)
    if not cancel:
        await session.execute(
            update(ConnectionTest)
            .where(ConnectionTest.id == UUID(test["id"]))
            .values(deadline=utc_now() - timedelta(minutes=1))
        )
        await session.commit()
    test = await step(client, test, "cancel" if cancel else "advance")
    expected = "canceled" if cancel else "timed_out"
    assert test["status"] == expected and test["cleanup_status"] == "waiting"
    assert github.pr["state"] == "closed" and github.branch
    github.push(test["id"])
    test = await step(client, test)
    assert test["status"] == expected and len(github.comments) == 1
    await session.execute(
        update(ConnectionTest)
        .where(ConnectionTest.id == UUID(test["id"]))
        .values(finished_at=utc_now() - timedelta(days=2))
    )
    await session.commit()
    test = await step(client, test)
    assert test["cleanup_status"] == "completed" and github.branch is None
    assert await session.get(ScheduleConfig, UUID(test["id"])) is None


async def test_worker_lease_prevents_duplicate_steps_and_preserves_concurrent_cancel(client, project, github, session):
    test = await start(client, project)
    repo = ConnectionTestRepository()
    claim = await repo.claim(session, UUID(test["id"]))
    assert claim is not None
    await session.commit()
    assert await repo.claim(session, UUID(test["id"])) is None
    await session.commit()
    canceled = await step(client, test, "cancel")
    assert canceled["cancel_requested"] is True and not github.writes
    row, token = claim
    await repo.finish_step(session, row, token)
    await session.commit()
    final = await step(client, test)
    assert final["status"] == "canceled" and not github.comments


async def test_other_project_cannot_control_test_and_settings_change_stops_dispatch(client, project, github):
    test = await step(client, await start(client, project))
    response = await client.post(f"/api/v1/projects/{uuid4()}/connection-tests/{test['id']}/advance")
    assert response.status_code == 404
    update_project = {key: project[key] for key in ("name", "github", "enabled")}
    update_project.update(name="Renamed", expected_revision=project["revision"])
    assert (await client.put(f"/api/v1/projects/{project['id']}", json=update_project)).status_code == 200
    test = await step(client, test)
    assert test["status"] == "canceled" and not github.comments


class ProbeJules:
    def __init__(self, github):
        self.github = github
        self.remote = None
        self.creates = []
        self.lose_response = False
        self.visible = True
        self.sources = True
        self.catalog_id = ""

    def respond(self, request):
        path, method = request.url.path, request.method
        if path.endswith("/sources"):
            return httpx.Response(
                200,
                json={
                    "sources": [{"name": "sources/opaque-app-id", "githubRepo": {"owner": "owner", "repo": "app"}}]
                    if self.sources
                    else []
                },
            )
        if path.endswith("/sessions") and method == "POST":
            body = json.loads(request.content)
            self.creates.append(body)
            self.remote = {
                "name": "sessions/probe",
                "title": body["title"],
                "state": "IN_PROGRESS",
                "url": "https://jules.google.com/session/probe",
                "outputs": [],
            }
            if self.lose_response:
                raise httpx.ReadTimeout("response lost", request=request)
            return httpx.Response(200, json=self.remote)
        if path.endswith("/sessions"):
            return httpx.Response(200, json={"sessions": [self.remote] if self.remote and self.visible else []})
        if path.endswith("/sessions/probe"):
            return httpx.Response(200, json=self.remote)
        raise AssertionError(f"Unexpected Jules {method} {path}")

    def complete(self, test_id):
        self.github.pr = {
            "number": 42,
            "title": "Jules test",
            "body": f"<!-- autohub-connection-test:{test_id} -->",
            "draft": False,
            "state": "open",
            "head": {"ref": "jules/generated-branch", "sha": "c" * 40, "repo": {"full_name": "owner/app"}},
            "base": {"ref": self.github.branch, "sha": "b" * 40},
            "html_url": "https://github.com/owner/app/pull/42",
        }
        self.github.push(test_id)
        assert self.remote is not None
        self.remote.update(state="COMPLETED", outputs=[{"pullRequest": {"url": self.github.pr["html_url"]}}])


@pytest.fixture
async def jules(client, session, github, monkeypatch):
    from app.features.ai_catalogs.models import AICatalog
    from app.features.ai_catalogs.providers import jules as jules_client

    connector = await client.post(
        "/api/v1/connectors",
        json={"name": "Jules probe", "provider": "jules", "credentials": {"token": "jules-test-token"}},
    )
    assert connector.status_code == 201
    catalog = AICatalog(
        key="probe-jules",
        name="Probe Jules",
        kind="jules",
        adapter="jules-api",
        connector_id=UUID(connector.json()["id"]),
        configured_concurrency=1,
        policy_config={"daily_task_limit": 100, "window": "rolling", "timezone": "UTC"},
    )
    session.add(catalog)
    await session.commit()
    scenario = ProbeJules(github)
    scenario.catalog_id = str(catalog.id)
    monkeypatch.setattr(
        jules_client,
        "create_jules_client",
        lambda token: httpx.AsyncClient(
            base_url=jules_client.JULES_API_BASE_URL, transport=httpx.MockTransport(scenario.respond)
        ),
    )
    original = github.respond

    def respond(request):
        if "/compare/" in request.url.path:
            return httpx.Response(200, json={"status": "ahead"})
        return original(request)

    github.respond = respond
    return scenario


async def start_jules(client, project, jules, request_id=None):
    result = await client.post(
        f"/api/v1/projects/{project['id']}/connection-tests",
        json={"request_id": request_id or str(uuid4()), "ai_catalog_id": jules.catalog_id},
    )
    assert result.status_code == 201, result.text
    return result.json()


async def test_jules_catalog_session_pr_ci_and_cleanup_without_adoption(client, project, github, jules, session):
    from app.features.ai_catalogs.models import AICatalogDispatch, AICatalogSession
    from app.features.project_management.pipeline_runs.models import PipelineRun

    test = await start_jules(client, project, jules)
    assert test["catalog_snapshot"]["key"] == "probe-jules"
    test = await step(client, test)
    assert test["phase"] == "dispatching" and github.pr is None
    test = await step(client, test)
    assert test["phase"] == "waiting_for_session"
    assert jules.creates[0]["sourceContext"] == {
        "source": "sources/opaque-app-id",
        "githubRepoContext": {"startingBranch": github.branch},
    }
    assert jules.creates[0]["automationMode"] == "AUTO_CREATE_PR"
    assert not github.comments
    jules.complete(test["id"])
    test = await step(client, test)
    assert test["status"] == "succeeded" and test["evidence"]["ci_status"] == "passed"
    test = await step(client, test)
    assert github.pr is not None
    assert test["cleanup_status"] == "completed" and github.pr["state"] == "closed"
    assert len(jules.creates) == 1
    assert list(await session.scalars(select(AICatalogDispatch)))
    assert not list(await session.scalars(select(AICatalogSession)))
    assert not list(await session.scalars(select(PipelineRun)))


async def test_jules_unknown_create_is_reconciled_without_duplicate_sessions(client, project, github, jules):
    test = await step(client, await start_jules(client, project, jules))
    jules.lose_response, jules.visible = True, False
    test = await step(client, test)
    assert test["phase"] == "dispatching" and test["evidence"]["create_attempted"]
    test = await step(client, test)
    assert test["phase"] == "dispatching" and len(jules.creates) == 1
    jules.visible = True
    test = await step(client, test)
    assert test["phase"] == "waiting_for_session" and len(jules.creates) == 1


async def test_cancel_jules_still_closes_late_pr_and_preserves_canceled_outcome(
    client, project, github, jules, session
):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    test = await step(client, test, "cancel")
    assert test["status"] == "canceled" and test["cleanup_status"] == "waiting"
    jules.complete(test["id"])
    test = await step(client, test)
    assert test["status"] == "canceled" and github.pr["state"] == "closed"
    await session.execute(
        update(ConnectionTest)
        .where(ConnectionTest.id == UUID(test["id"]))
        .values(finished_at=utc_now() - timedelta(days=2))
    )
    await session.commit()
    test = await step(client, test)
    assert test["cleanup_status"] == "completed" and len(jules.creates) == 1


@pytest.mark.parametrize("hidden_refs", [False, True])
async def test_jules_output_is_blocked_before_scheduler_discovers_it(client, project, github, jules, hidden_refs):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    jules.complete(test["id"])
    if hidden_refs:
        # The ancestor guard still blocks an output with a renamed head and retargeted base, before its ID is known.
        github.pr["base"]["ref"] = "main"
        github.pr["body"] = ""
    response = await client.post(
        f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 42, "implemented": True}
    )
    assert response.status_code == 422, response.text
    assert "Connection test" in response.text


async def test_jules_test_cannot_bypass_final_merge_gate(client, project, github, jules, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from app.features.project_management.pipeline_runs.usecases.progress import PipelineRunProgress
    from app.features.project_management.pipelines.services import PipelineObservationService
    from app.features.project_management.projects.errors import ProjectError

    test = await step(client, await step(client, await start_jules(client, project, jules)))
    jules.complete(test["id"])
    github.pr["base"]["ref"] = "main"
    progress = PipelineRunProgress(
        MagicMock(), MagicMock(), PipelineObservationService(AsyncMock(return_value="test")), None
    )
    # Simulate a run that was enrolled before its head was replaced with a test descendant.
    monkeypatch.setattr(
        progress,
        "_validate",
        AsyncMock(
            return_value=(
                SimpleNamespace(branch="old-normal-branch", pull_number=42, pull_snapshot={}),
                SimpleNamespace(
                    github_repository="owner/app", github_connector_id=UUID(project["github"]["github_connector_id"])
                ),
            )
        ),
    )
    with pytest.raises(ProjectError, match="Connection test"):
        await progress._authorize_merge(MagicMock())


async def test_catalog_identity_retries_and_admission_hold(client, project, github, jules, session):
    from app.features.ai_catalogs.models import AICatalog

    test = await start_jules(client, project, jules)
    assert (await start_jules(client, project, jules, test["id"]))["id"] == test["id"]
    conflict = await client.post(
        f"/api/v1/projects/{project['id']}/connection-tests",
        json={"request_id": test["id"], "ai_catalog_id": str(uuid4())},
    )
    assert conflict.status_code == 409
    test = await step(client, test)
    await session.execute(
        update(AICatalog)
        .where(AICatalog.id == UUID(jules.catalog_id))
        .values(availability_state="quota_blocked", available_at=utc_now() + timedelta(hours=2))
    )
    await session.commit()
    test = await step(client, test)
    assert test["phase"] == "dispatching" and not jules.creates
    assert "quota-blocked" in test["detail"]


async def test_jules_missing_source_does_not_create_github_resources_or_session(client, project, github, jules):
    jules.sources = False
    test = await step(client, await start_jules(client, project, jules))
    assert test["status"] == "failed" and not github.writes and not jules.creates


async def test_jules_wrong_base_closes_owned_pr_without_verifying(client, project, github, jules):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    jules.complete(test["id"])
    github.pr["base"]["ref"] = "main"
    test = await step(client, test)
    assert test["status"] == "failed"
    test = await step(client, test)
    assert test["status"] == "failed" and github.pr["state"] == "closed"


async def test_probe_holds_shared_catalog_capacity_until_execution_finishes(client, project, github, jules, session):
    from app.features.ai_catalogs.repos import AICatalogRepository
    from app.features.ai_catalogs.services import AICatalogService

    catalogs = AICatalogService(AICatalogRepository())
    catalog_id = UUID(jules.catalog_id)
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    assert await catalogs.repo.active_dispatch_count(session, catalog_id) == 1
    admission = await catalogs.request_dispatch(session, catalog_id, None, "other-session", utc_now())
    assert admission.rejection == "AI catalog has reached its concurrency limit"
    await session.commit()
    jules.complete(test["id"])
    test = await step(client, await step(client, test))
    assert test["cleanup_status"] == "completed"
    assert await catalogs.repo.active_dispatch_count(session, catalog_id) == 0
    admission = await catalogs.request_dispatch(session, catalog_id, None, "other-session", utc_now())
    assert admission.rejection is None


async def test_recipe_options_report_provider_specific_prerequisites(client, project, jules, session):
    from app.features.ai_catalogs.models import AICatalog
    from app.features.configuration.connectors.models import Connector

    session.add(AICatalog(key="probe-codex", name="Probe Codex", kind="codex", adapter="codex-github-mention"))
    await session.commit()
    path = f"/api/v1/projects/{project['id']}/connection-tests/options"
    options = (await client.get(path)).json()
    codex = next(o for o in options if o["kind"] == "codex")
    option = next(o for o in options if o["ai_catalog_id"] == jules.catalog_id)
    assert codex["ready"] and option["ready"]
    assert any(r["key"] == "codex_environment" for r in codex["spec"]["requirements"])
    assert any(r["key"] == "jules_source" for r in option["spec"]["requirements"])
    catalog = await session.get(AICatalog, UUID(jules.catalog_id))
    await session.execute(update(Connector).where(Connector.id == catalog.connector_id).values(enabled=False))
    await session.commit()
    option = next(o for o in (await client.get(path)).json() if o["ai_catalog_id"] == jules.catalog_id)
    assert not option["ready"]
    assert {"key": "jules_connector", "status": "missing"} in option["requirements"]
    response = await client.post(
        path.removesuffix("/options"),
        json={
            "request_id": str(uuid4()),
            "ai_catalog_id": jules.catalog_id,
        },
    )
    assert response.status_code == 422


async def test_configuration_fingerprint_ignores_quota_but_detects_credential_rotation(client, project, jules, session):
    from app.features.ai_catalogs.models import AICatalog
    from app.features.configuration.connectors.models import Connector

    test = await start_jules(client, project, jules)
    assert test["configuration_current"]
    path = f"/api/v1/projects/{project['id']}/connection-tests"
    await session.execute(
        update(AICatalog)
        .where(AICatalog.id == UUID(jules.catalog_id))
        .values(
            name="Renamed",
            revision=12,
            availability_state="quota_blocked",
            available_at=utc_now() + timedelta(hours=2),
        )
    )
    await session.commit()
    assert (await client.get(path)).json()[0]["configuration_current"]
    catalog = await session.get(AICatalog, UUID(jules.catalog_id))
    # Changing the encrypted version is sufficient to test invalidation; no decryption should be attempted.
    await session.execute(
        update(Connector)
        .where(Connector.id == catalog.connector_id)
        .values(
            credentials_ciphertext=b"rotated-credentials",
        )
    )
    await session.commit()
    assert not (await client.get(path)).json()[0]["configuration_current"]
    test = await step(client, test)
    assert test["status"] == "canceled"
    assert not jules.creates


async def test_cleanup_closes_unknown_jules_output_without_provider_credentials(
    client, project, github, jules, session
):
    from app.features.ai_catalogs.models import AICatalog
    from app.features.configuration.connectors.models import Connector

    test = await step(client, await step(client, await start_jules(client, project, jules)))
    catalog = await session.get(AICatalog, UUID(jules.catalog_id))
    await session.execute(update(Connector).where(Connector.id == catalog.connector_id).values(enabled=False))
    await session.commit()
    jules.complete(test["id"])
    test = await step(client, test, "cancel")
    assert test["status"] == "canceled" and test["cleanup_status"] == "waiting"
    assert github.pr["state"] == "closed"
    assert test["evidence"]["owned_pulls"]["42"]["branch"] == "jules/generated-branch"
    assert test["evidence"]["cleanup_warning"]
    await session.execute(
        update(ConnectionTest)
        .where(ConnectionTest.id == UUID(test["id"]))
        .values(
            finished_at=utc_now() - timedelta(days=2),
        )
    )
    await session.commit()
    test = await step(client, test)
    assert test["cleanup_status"] == "waiting"
    assert test["evidence"]["output_discovery_pending"]
    # Recovering provider access establishes that there can be no more output.
    await session.execute(update(Connector).where(Connector.id == catalog.connector_id).values(enabled=True))
    await session.commit()
    test = await step(client, test)
    assert test["cleanup_status"] == "completed"
    assert "cleanup_warning" not in test["evidence"]
    assert len(jules.creates) == 1


async def test_completed_jules_execution_releases_capacity_before_failed_cleanup(
    client, project, github, jules, session
):
    from app.features.ai_catalogs.repos import AICatalogRepository

    test = await step(client, await step(client, await start_jules(client, project, jules)))
    jules.complete(test["id"])
    # CI can remain pending after the provider has already finished its work.
    github.ci = "skipped"
    test = await step(client, test)
    assert test["status"] == "running" and test["evidence"]["execution_finished"]
    repo = AICatalogRepository()
    assert await repo.active_dispatch_count(session, UUID(jules.catalog_id)) == 0
    github.fail_cleanup = True
    test = await step(client, test, "cancel")
    assert test["cleanup_status"] == "failed"
    assert await repo.active_dispatch_count(session, UUID(jules.catalog_id)) == 0


async def test_unknown_execution_capacity_expires_even_when_cleanup_keeps_failing(
    client, project, github, jules, session
):
    from app.features.ai_catalogs.repos import AICatalogRepository

    test = await step(client, await step(client, await start_jules(client, project, jules)))
    test = await step(client, test, "cancel")
    repo = AICatalogRepository()
    assert await repo.active_dispatch_count(session, UUID(jules.catalog_id)) == 1
    await session.execute(
        update(ConnectionTest)
        .where(ConnectionTest.id == UUID(test["id"]))
        .values(
            finished_at=utc_now() - timedelta(days=2),
            cleanup_status="failed",
        )
    )
    await session.commit()
    assert await repo.active_dispatch_count(session, UUID(jules.catalog_id)) == 0
    assert await ConnectionTestRepository().protected_heads(session, "owner/app") == [test["evidence"]["initial_sha"]]


async def test_completed_history_skips_ancestry_checks_but_keeps_all_owned_pr_ids(
    client, project, github, jules, session
):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    repo = ConnectionTestRepository()
    assert await repo.protected_heads(session, "owner/app")
    jules.complete(test["id"])
    test = await step(client, await step(client, test))
    assert test["cleanup_status"] == "completed"
    assert await repo.protected_heads(session, "owner/app") == []
    assert await repo.owns_pull(session, "owner/app", 42)
    evidence = {**test["evidence"], "pull_number": 43}
    await session.execute(update(ConnectionTest).where(ConnectionTest.id == UUID(test["id"])).values(evidence=evidence))
    await session.commit()
    # A later output replacing the primary PR must not remove earlier owned PR IDs from protection.
    assert await repo.owns_pull(session, "owner/app", 42)
    assert await repo.owns_pull(session, "owner/app", 43)
    assert not await repo.owns_pull(session, "owner/app", 99)


async def test_codex_quota_reply_records_catalog_block_once(client, project, github, session):
    from app.features.ai_catalogs.models import AICatalog

    test = await step(client, await step(client, await start(client, project)))
    github.comments.append(
        {
            "id": 2,
            "user": {"login": "chatgpt-codex-connector[bot]"},
            "body": "You reached a Codex usage limit.",
            "html_url": "https://github.com/owner/app/pull/42#issuecomment-2",
        }
    )
    test = await step(client, test)
    assert test["status"] == "failed" and test["evidence"]["quota_recorded"]
    catalog = await session.get(AICatalog, UUID(test["ai_catalog_id"]))
    assert catalog.availability_state == "quota_blocked"
    revision = catalog.revision
    await step(client, test)
    await session.refresh(catalog)
    assert catalog.revision == revision


async def test_registered_recipe_runs_without_provider_branches_in_engine(
    client, project, github, session, monkeypatch
):
    from app.features.ai_catalogs.models import AICatalog
    from app.features.project_management.connection_tests.adapters.registry import ADAPTERS
    from app.features.project_management.connection_tests.adapters.specs import GITHUB_REQUIREMENT, ConnectionTestSpec

    class CustomRecipe:
        spec = ConnectionTestSpec(
            key="custom-test",
            title="Custom recipe",
            description="Custom checks",
            requirements=[GITHUB_REQUIREMENT],
            delivery_key="receipt",
            phases={"custom_observation": "Observe custom evidence"},
        )

        async def prepare(self, row, context):
            row.phase = "dispatching"

        async def dispatch(self, row, context, *, create_once):
            row.evidence.update(receipt="delivered", delivered_at=utc_now().isoformat())
            row.phase = "custom_observation"

        async def observe(self, row, context):
            row.status = "succeeded"
            row.evidence["execution_finished"] = True

        async def cleanup(self, row, context):
            row.cleanup_status = "completed"

    monkeypatch.setitem(ADAPTERS, ("codex", "custom-test"), CustomRecipe())
    catalog = AICatalog(key="custom-test", name="Custom", kind="codex", adapter="custom-test")
    session.add(catalog)
    await session.commit()
    path = f"/api/v1/projects/{project['id']}/connection-tests"
    response = await client.post(path, json={"request_id": str(uuid4()), "ai_catalog_id": str(catalog.id)})
    assert response.status_code == 201, response.text
    test = response.json()
    for _ in range(4):
        test = await step(client, test)
    assert test["status"] == "succeeded" and test["cleanup_status"] == "completed"
    assert test["test_spec"]["phases"]["custom_observation"] == "Observe custom evidence"
    assert test["evidence"]["delivery_recorded"]
    assert not github.writes


async def test_all_jules_outputs_are_recorded_and_closed_when_provider_returns_extra_prs(
    client, project, github, jules
):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    jules.complete(test["id"])
    extra = deepcopy(github.pr)
    extra.update(number=43, html_url="https://github.com/owner/app/pull/43")
    extra["head"]["ref"] = "jules/extra-output"
    jules.remote["outputs"].append({"pullRequest": {"url": extra["html_url"]}})
    original = github.respond

    def respond(request):
        if request.url.path.endswith("/pulls/43"):
            if request.method == "PATCH":
                extra.update(json.loads(request.content))
            return httpx.Response(200, json=deepcopy(extra))
        return original(request)

    github.respond = respond
    test = await step(client, test)
    assert test["status"] == "failed"
    assert set(test["evidence"]["owned_pulls"]) == {"42", "43"}
    test = await step(client, test)
    assert test["cleanup_status"] == "waiting"
    assert github.pr["state"] == extra["state"] == "closed"


async def test_lost_draft_creation_response_reconciles_preparation_before_dispatch(client, project, github):
    original = github.respond
    lose_response = True

    def respond(request):
        nonlocal lose_response
        response = original(request)
        if request.method == "POST" and request.url.path.endswith("/pulls") and lose_response:
            lose_response = False
            raise httpx.ReadTimeout("Draft PR response lost", request=request)
        return response

    github.respond = respond
    test = await step(client, await start(client, project))
    assert test["phase"] == "preparing" and test["status"] == "running"
    test = await step(client, test)
    assert test["phase"] == "dispatching"
    test = await step(client, test)
    assert test["phase"] == "waiting_for_push" and len(github.comments) == 1
    assert len([w for w in github.writes if w[0] == "POST" and w[1].endswith("/pulls")]) == 1
