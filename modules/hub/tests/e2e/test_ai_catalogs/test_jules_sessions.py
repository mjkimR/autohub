import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from app.features.ai_catalogs.models import (
    AICatalog,
    AICatalogDispatch,
    AICatalogKind,
    AICatalogSession,
    AICatalogState,
)
from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.services import AICatalogService
from app.features.configuration.connectors.models import Connector
from app.features.execution.tasks.domains.jules import service as jules_service
from app.features.execution.tasks.domains.jules.client import JULES_API_BASE_URL
from app.features.execution.tasks.domains.jules.service import JulesSessionPayload, JulesSessionService
from app.features.project_management.pipeline_runs.models import ExecutionAttempt, PipelineRun
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.pipelines.repos import PipelineObservationRepository
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService
from app_testing_base import hours_ago
from sqlalchemy import select

from tests.utils.assertions import assert_status_code

pytestmark = pytest.mark.e2e


class FakeJules:
    def __init__(self) -> None:
        self.responses: dict[tuple[str, str], tuple[int, dict]] = {}
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self.responses[(request.method, request.url.path)]
        return httpx.Response(status, json=body)


@pytest.fixture
def jules(monkeypatch) -> FakeJules:
    fake = FakeJules()
    monkeypatch.setattr(
        jules_service,
        "create_jules_client",
        lambda api_key: httpx.AsyncClient(
            base_url=JULES_API_BASE_URL,
            headers={"X-Goog-Api-Key": api_key},
            transport=httpx.MockTransport(fake.handle),
        ),
    )
    return fake


async def make_catalog(session, *, limit: int = 100, with_connector: bool = True) -> SimpleNamespace:
    connector_id = None
    if with_connector:
        connector = Connector(
            name=f"jules-{uuid4().hex[:8]}",
            provider="jules",
            config={},
            enabled=True,
            credentials_ciphertext=b"sealed",
            credentials_nonce=b"0" * 12,
            credential_key_version="test",
        )
        session.add(connector)
        await session.flush()
        connector_id = connector.id
    catalog = AICatalog(
        key=f"jules-{uuid4().hex[:8]}",
        name="Jules",
        kind=AICatalogKind.JULES,
        adapter="jules-api",
        connector_id=connector_id,
        enabled=True,
        availability_state=AICatalogState.NORMAL,
        configured_concurrency=15,
        policy_config={"daily_task_limit": limit, "window": "rolling", "timezone": "UTC"},
        revision=1,
    )
    session.add(catalog)
    await session.flush()
    created = SimpleNamespace(id=catalog.id, key=catalog.key)
    await session.commit()
    return created


def make_service() -> JulesSessionService:
    cipher = MagicMock()
    cipher.decrypt = AsyncMock(return_value={"token": "jules-key"})
    catalogs = AICatalogService(AICatalogRepository())
    observer = PipelineObservationService(PipelineObservationRepository(), cipher)
    runs = PipelineRunUseCase(PipelineRunRepository(), ProjectService(ProjectRepository()), observer, catalogs)
    return JulesSessionService(catalogs, cipher, runs)


PULL_REQUEST_NUMBER = 9
PULL_REQUEST_URL = f"https://github.com/owner/app/pull/{PULL_REQUEST_NUMBER}"


@pytest.fixture
def github(monkeypatch) -> list[str]:
    """A GitHub API that serves the pull request a Jules session opened and records what was read."""
    paths: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET", "Adoption must never mutate GitHub"
        paths.append(request.url.path)
        if request.url.path != f"/repos/owner/app/pulls/{PULL_REQUEST_NUMBER}":
            return httpx.Response(404, json={"message": "not found"})
        return httpx.Response(
            200,
            json={
                "number": PULL_REQUEST_NUMBER,
                "state": "open",
                "html_url": PULL_REQUEST_URL,
                "title": "Tidy stale dependencies",
                "body": "Opened by Jules.",
                "head": {"ref": "jules/tidy", "sha": "a" * 40, "repo": {"full_name": "owner/app"}},
                "base": {"ref": "main", "sha": "b" * 40, "repo": {"full_name": "owner/app"}},
            },
        )

    monkeypatch.setattr(
        pipeline_services,
        "create_github_client",
        lambda token: httpx.AsyncClient(base_url="https://api.github.com", transport=httpx.MockTransport(respond)),
    )
    return paths


@pytest.fixture
async def project(client, github) -> dict:
    connector = await client.post(
        "/api/v1/connectors",
        json={"name": "github-account", "provider": "github", "credentials": {"token": "github-test-token"}},
    )
    assert_status_code(connector, 201)
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Application",
            "repository": "owner/app",
            "github_connector_id": connector.json()["id"],
            "verification": {"workflow": "ci.yml", "required_jobs": ["lint"], "event": "pull_request"},
        },
    )
    assert_status_code(response, 201)
    return response.json()


def completed_session(name: str, *, pull_request_url: str | None = None) -> dict:
    remote: dict = {"name": name, "state": "COMPLETED", "url": f"https://jules.google/{name}"}
    if pull_request_url is not None:
        remote["outputs"] = [{"pullRequest": {"url": pull_request_url}}]
    return remote


def activities(*messages: str) -> dict:
    return {"activities": [{"agentMessaged": {"message": message}} for message in messages]}


async def track(
    session, catalog, *, work_type: str, name: str, repository: str | None = "owner/app"
) -> AICatalogSession:
    row = AICatalogSession(
        ai_catalog_id=catalog.id,
        title=f"{work_type} session",
        work_type=work_type,
        repository=repository,
        state="in_progress",
        external_name=name,
    )
    session.add(row)
    await session.commit()
    return row


def payload(catalog_key: str, **overrides) -> JulesSessionPayload:
    return JulesSessionPayload(
        catalog_key=catalog_key,
        repository="owner/app",
        title="Weekly hygiene report",
        prompt="Report stale dependencies.",
        **overrides,
    )


async def sessions_of(session, catalog_id) -> list[AICatalogSession]:
    session.expire_all()
    return list(
        (await session.scalars(select(AICatalogSession).where(AICatalogSession.ai_catalog_id == catalog_id))).all()
    )


async def test_an_admitted_session_is_created_counted_and_tracked(client, session, jules):
    catalog = await make_catalog(session)
    jules.responses[("POST", "/v1alpha/sessions")] = (
        200,
        {"name": "sessions/42", "state": "QUEUED", "url": "https://jules.google/session/42"},
    )

    session_id = await make_service().start(payload(catalog.key, auto_create_pr=True), None)

    [request] = jules.requests
    body = json.loads(request.content)
    assert request.headers["X-Goog-Api-Key"] == "jules-key"
    assert body["sourceContext"] == {
        "source": "sources/github/owner/app",
        "githubRepoContext": {"startingBranch": "main"},
    }
    assert body["automationMode"] == "AUTO_CREATE_PR"
    assert body["title"] == f"Weekly hygiene report [hub-session:{session_id}]"
    assert body["prompt"].startswith("Report stale dependencies.\n\n")
    assert "open one pull request" in body["prompt"]
    [tracked] = await sessions_of(session, catalog.id)
    assert (tracked.id, tracked.state, tracked.external_name) == (session_id, "queued", "sessions/42")
    assert (tracked.work_type, tracked.repository) == ("task", "owner/app")
    ledger = await session.scalars(
        select(AICatalogDispatch.dispatch_key).where(AICatalogDispatch.ai_catalog_id == catalog.id)
    )
    assert ledger.all() == [f"session:{session_id}"]


async def test_admitting_work_prunes_expired_ledger_rows_of_every_catalog(client, session, jules):
    catalog = await make_catalog(session)
    idle_catalog = await make_catalog(session)
    session.add_all(
        [
            AICatalogDispatch(
                ai_catalog_id=idle_catalog.id, dispatch_key="session:expired", admitted_at=hours_ago(31 * 24)
            ),
            AICatalogDispatch(ai_catalog_id=idle_catalog.id, dispatch_key="session:kept", admitted_at=hours_ago(24)),
        ]
    )
    await session.commit()
    jules.responses[("POST", "/v1alpha/sessions")] = (200, {"name": "sessions/42", "state": "QUEUED"})

    await make_service().start(payload(catalog.key), None)

    ledger = await session.scalars(
        select(AICatalogDispatch.dispatch_key).where(AICatalogDispatch.ai_catalog_id == idle_catalog.id)
    )
    assert ledger.all() == ["session:kept"]


async def test_reaching_the_daily_limit_holds_the_catalog_without_calling_jules(client, session, jules):
    catalog = await make_catalog(session, limit=1)
    session.add(
        AICatalogDispatch(
            ai_catalog_id=catalog.id,
            dispatch_key="session:earlier",
            admitted_at=hours_ago(1),
        )
    )
    await session.commit()

    with pytest.raises(ProjectError) as rejected:
        await make_service().start(payload(catalog.key), None)

    assert rejected.value.status_code == 409
    assert jules.requests == []
    assert await sessions_of(session, catalog.id) == []
    held = await session.get(AICatalog, catalog.id)
    assert held is not None and held.availability_state == AICatalogState.QUOTA_BLOCKED


async def test_a_rate_limited_create_fails_the_session_and_holds_the_catalog(client, session, jules):
    catalog = await make_catalog(session)
    jules.responses[("POST", "/v1alpha/sessions")] = (429, {"error": {"status": "RESOURCE_EXHAUSTED"}})

    with pytest.raises(ProjectError) as rejected:
        await make_service().start(payload(catalog.key), None)

    assert rejected.value.status_code == 429
    [tracked] = await sessions_of(session, catalog.id)
    assert tracked.state == "failed"
    held = await session.get(AICatalog, catalog.id)
    assert held is not None and held.availability_state == AICatalogState.QUOTA_BLOCKED


async def test_sync_adopts_an_unconfirmed_session_and_releases_a_finished_one(client, session, jules):
    catalog = await make_catalog(session)
    unconfirmed_id, running_id = uuid4(), uuid4()
    unconfirmed_title = f"Report [hub-session:{unconfirmed_id}]"
    session.add_all(
        [
            AICatalogSession(id=unconfirmed_id, ai_catalog_id=catalog.id, title=unconfirmed_title, state="dispatching"),
            AICatalogSession(
                id=running_id,
                ai_catalog_id=catalog.id,
                title="Hygiene",
                state="in_progress",
                external_name="sessions/7",
            ),
        ]
    )
    await session.commit()
    jules.responses[("GET", "/v1alpha/sessions")] = (
        200,
        {"sessions": [{"name": "sessions/8", "title": unconfirmed_title, "state": "IN_PROGRESS"}]},
    )
    jules.responses[("GET", "/v1alpha/sessions/7")] = (
        200,
        completed_session("sessions/7", pull_request_url="https://github.com/owner/app/pull/9"),
    )
    jules.responses[("GET", "/v1alpha/sessions/7/activities")] = (200, activities("Working…", "Opened PR #9."))

    await make_service().sync(catalog.key)

    tracked = {row.id: row for row in await sessions_of(session, catalog.id)}
    assert (tracked[unconfirmed_id].state, tracked[unconfirmed_id].external_name) == ("in_progress", "sessions/8")
    assert (tracked[running_id].state, tracked[running_id].pull_request_url) == (
        "completed",
        "https://github.com/owner/app/pull/9",
    )
    assert tracked[running_id].result_summary == "Opened PR #9."
    # No project owns owner/app here, so the pull request stays a link.
    assert tracked[running_id].pipeline_run_id is None
    assert tracked[running_id].failure_detail == "No project is connected to the session's repository"
    assert await AICatalogRepository().active_dispatch_count(session, catalog.id) == 1


async def test_a_catalog_without_a_jules_connector_is_rejected(client, session, jules):
    catalog = await make_catalog(session, with_connector=False)

    with pytest.raises(ProjectError) as rejected:
        await make_service().start(payload(catalog.key), None)

    assert rejected.value.status_code == 422
    assert jules.requests == []


async def test_a_completed_task_session_has_its_pull_request_adopted_as_implemented(
    client, session, jules, github, project
):
    catalog = await make_catalog(session)
    row = await track(session, catalog, work_type="task", name="sessions/21")
    jules.responses[("GET", "/v1alpha/sessions/21")] = (
        200,
        completed_session("sessions/21", pull_request_url=PULL_REQUEST_URL),
    )
    jules.responses[("GET", "/v1alpha/sessions/21/activities")] = (200, activities("Tidied dependencies."))

    await make_service().sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert tracked.id == row.id and tracked.failure_detail is None
    assert tracked.result_summary == "Tidied dependencies."
    run = await session.get(PipelineRun, tracked.pipeline_run_id)
    assert run is not None
    assert (run.state, run.pull_number, run.branch, str(run.project_id)) == (
        "awaiting_ci",
        PULL_REQUEST_NUMBER,
        "jules/tidy",
        project["id"],
    )
    [attempt] = (
        await session.scalars(select(ExecutionAttempt).where(ExecutionAttempt.pipeline_run_id == run.id))
    ).all()
    assert (attempt.kind, attempt.state, attempt.external_status) == (
        "implementation",
        "running",
        "implemented-externally",
    )
    assert github == [f"/repos/owner/app/pulls/{PULL_REQUEST_NUMBER}"]

    # A later sync leaves the finished session and its run alone.
    await make_service().sync(catalog.key)
    assert len(github) == 1


async def test_a_completed_report_session_keeps_its_final_message_and_opens_nothing(
    client, session, jules, github, project
):
    catalog = await make_catalog(session)
    await track(session, catalog, work_type="report", name="sessions/22")
    jules.responses[("GET", "/v1alpha/sessions/22")] = (200, completed_session("sessions/22"))
    jules.responses[("GET", "/v1alpha/sessions/22/activities")] = (
        200,
        activities("Collecting…", "## Weekly report\n\n- 3 stale dependencies"),
    )

    await make_service().sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert tracked.state == "completed"
    assert tracked.result_summary == "## Weekly report\n\n- 3 stale dependencies"
    assert (tracked.pull_request_url, tracked.pipeline_run_id, tracked.failure_detail) == (None, None, None)
    assert github == []
    assert (await session.scalars(select(PipelineRun))).all() == []


async def test_a_task_session_without_a_pull_request_is_noted(client, session, jules, github, project):
    catalog = await make_catalog(session)
    await track(session, catalog, work_type="task", name="sessions/23")
    jules.responses[("GET", "/v1alpha/sessions/23")] = (200, completed_session("sessions/23"))
    jules.responses[("GET", "/v1alpha/sessions/23/activities")] = (200, activities("Nothing to change."))

    await make_service().sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert tracked.result_summary == "Nothing to change."
    assert tracked.failure_detail == "Task session completed without opening a pull request"
    assert (await session.scalars(select(PipelineRun))).all() == []


async def test_a_project_can_opt_out_of_adopting_session_pull_requests(client, session, jules, github, project):
    automation = {**project["github"]["automation"], "auto_enroll_sessions": False}
    updated = await client.put(
        f"/api/v1/projects/{project['id']}",
        json={
            "name": project["name"],
            "enabled": True,
            "expected_revision": project["revision"],
            "github": {**project["github"], "automation": automation},
        },
    )
    assert_status_code(updated, 200)
    catalog = await make_catalog(session)
    await track(session, catalog, work_type="task", name="sessions/24")
    jules.responses[("GET", "/v1alpha/sessions/24")] = (
        200,
        completed_session("sessions/24", pull_request_url=PULL_REQUEST_URL),
    )
    jules.responses[("GET", "/v1alpha/sessions/24/activities")] = (200, activities("Done."))

    await make_service().sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert tracked.pipeline_run_id is None
    assert tracked.failure_detail == "The project does not adopt session pull requests"
    assert github == []


async def test_a_pull_request_outside_the_session_repository_is_not_adopted(client, session, jules, github, project):
    catalog = await make_catalog(session)
    await track(session, catalog, work_type="task", name="sessions/25", repository="owner/other")
    jules.responses[("GET", "/v1alpha/sessions/25")] = (
        200,
        completed_session("sessions/25", pull_request_url=PULL_REQUEST_URL),
    )
    jules.responses[("GET", "/v1alpha/sessions/25/activities")] = (200, activities("Done."))

    await make_service().sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert tracked.pipeline_run_id is None
    assert tracked.failure_detail == "Pull request is not in the session's repository"
    assert github == []


async def test_an_unreadable_activity_log_leaves_the_summary_empty(client, session, jules, github, project):
    catalog = await make_catalog(session)
    await track(session, catalog, work_type="report", name="sessions/26")
    jules.responses[("GET", "/v1alpha/sessions/26")] = (200, completed_session("sessions/26"))
    jules.responses[("GET", "/v1alpha/sessions/26/activities")] = (500, {"error": "boom"})

    await make_service().sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert (tracked.state, tracked.result_summary) == ("completed", None)


async def test_a_session_waiting_for_a_person_is_failed_and_releases_its_slot(client, session, jules):
    catalog = await make_catalog(session)
    await track(session, catalog, work_type="report", name="sessions/31")
    jules.responses[("GET", "/v1alpha/sessions/31")] = (
        200,
        {"name": "sessions/31", "state": "AWAITING_USER_FEEDBACK", "url": "https://jules.google/sessions/31"},
    )

    await make_service().sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert tracked.state == "failed"
    assert "awaiting_user_feedback" in (tracked.failure_detail or "")
    assert await AICatalogRepository().open_session_count(session, catalog.id) == 0


async def test_adoption_left_unfinished_by_a_crash_is_retried_on_the_next_sync(client, session, jules, github, project):
    catalog = await make_catalog(session)
    # A session completed with a pull request but no verdict: the hub stopped between completion and adoption.
    row = await track(session, catalog, work_type="task", name="sessions/41")
    row.state = "completed"
    row.pull_request_url = PULL_REQUEST_URL
    await session.commit()

    await make_service().sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert tracked.pipeline_run_id is not None and tracked.failure_detail is None
    assert github == [f"/repos/owner/app/pulls/{PULL_REQUEST_NUMBER}"]


async def test_an_unexpected_adoption_error_is_recorded_and_does_not_stop_the_sync(
    client, session, jules, github, project, monkeypatch
):
    catalog = await make_catalog(session)
    row = await track(session, catalog, work_type="task", name="sessions/42")
    row.state = "completed"
    row.pull_request_url = PULL_REQUEST_URL
    await session.commit()
    service = make_service()

    async def explode(*args, **kwargs):
        raise RuntimeError("credential store unreachable")

    monkeypatch.setattr(service.runs, "enroll", explode)

    await service.sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert tracked.pipeline_run_id is None
    assert tracked.failure_detail == "Pull request adoption failed: credential store unreachable"


async def test_a_pull_request_enrolled_by_someone_else_is_linked_to_the_session(
    client, session, jules, github, project
):
    catalog = await make_catalog(session)
    enrolled = await client.post(
        f"/api/v1/projects/{project['id']}/runs", json={"pull_number": PULL_REQUEST_NUMBER, "implemented": True}
    )
    assert_status_code(enrolled, 201)
    row = await track(session, catalog, work_type="task", name="sessions/43")
    row.state = "completed"
    row.pull_request_url = PULL_REQUEST_URL
    await session.commit()

    await make_service().sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert (str(tracked.pipeline_run_id), tracked.failure_detail) == (enrolled.json()["id"], None)


async def test_a_final_message_past_the_page_budget_is_not_guessed(client, session, jules, monkeypatch):
    from app.features.execution.tasks.domains.jules import client as jules_client

    monkeypatch.setattr(jules_client, "ACTIVITY_PAGE_LIMIT", 1)
    catalog = await make_catalog(session)
    await track(session, catalog, work_type="report", name="sessions/44")
    jules.responses[("GET", "/v1alpha/sessions/44")] = (200, completed_session("sessions/44"))
    jules.responses[("GET", "/v1alpha/sessions/44/activities")] = (
        200,
        {**activities("Halfway there."), "nextPageToken": "page-2"},
    )

    await make_service().sync(catalog.key)

    [tracked] = await sessions_of(session, catalog.id)
    assert (tracked.state, tracked.result_summary) == ("completed", None)
