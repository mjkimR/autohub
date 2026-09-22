from datetime import timedelta
from uuid import UUID

import httpx
import pytest
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.work_plans.models import WorkItem
from app_layer_base.core.database.transaction import AsyncTransaction
from app_testing_base import utc_now
from tests.integration.features.project_management.work_plans.test_work_plans import create, due, get

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_uncertain_pr_recovers_after_temporary_lookup_404(client, setup_work, session, monkeypatch):
    project, github, worker, _ = setup_work
    plan = await create(client, project)
    github.lose_pull_response = True
    await worker.advance_project(UUID(project["id"]))
    assert len(github.pulls) == 1
    assert (await get(client, project, plan))["items"][0]["state"] == "preparing"
    original = github.respond

    def missing_permission(request):
        if request.method == "GET" and request.url.path == "/repos/owner/app/pulls":
            return httpx.Response(404, json={"message": "Not Found"})
        return original(request)

    with monkeypatch.context() as patch:
        patch.setattr(github, "respond", missing_permission)
        await due(session)
        await worker.advance_project(UUID(project["id"]))
    # The same PR is accessible again; reconciliation should link it without a new PR.
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    actual = (await get(client, project, plan))["items"][0]
    assert actual["pipeline_run_id"] is not None, actual
    assert len(github.pulls) == 1


@pytest.mark.parametrize("headers", [{}, {"retry-after": "600"}])
async def test_temporary_pr_creation_422_recovers(client, setup_work, session, monkeypatch, headers):
    project, github, worker, _ = setup_work
    plan = await create(client, project)
    original = github.respond

    def temporary_rejection(request):
        if request.method == "POST" and request.url.path == "/repos/owner/app/pulls":
            return httpx.Response(
                422, headers=headers, json={"message": "Validation failed, or the endpoint has been spammed."}
            )
        return original(request)

    before = utc_now()
    with monkeypatch.context() as patch:
        patch.setattr(github, "respond", temporary_rejection)
        await worker.advance_project(UUID(project["id"]))
    first = (await get(client, project, plan))["items"][0]
    assert first["state"] == "preparing"
    if headers:
        async with AsyncTransaction() as tx:
            row = await tx.get(WorkItem, UUID(first["id"]))
            assert row is not None and row.next_action_at is not None
            assert as_utc(row.next_action_at) >= before + timedelta(seconds=600)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    actual = (await get(client, project, plan))["items"][0]
    assert actual["pipeline_run_id"] is not None, actual


@pytest.mark.parametrize("lookup_status", [403, 404, 500])
async def test_private_ref_404_without_readable_listing_remains_retryable(
    client, setup_work, session, monkeypatch, lookup_status
):
    project, github, worker, _ = setup_work
    plan = await create(client, project)
    original = github.respond

    def unreadable_refs(request):
        if request.url.path == "/repos/owner/app/git/ref/heads/main":
            return httpx.Response(404)
        if "/git/matching-refs/" in request.url.path:
            return httpx.Response(lookup_status)
        return original(request)

    with monkeypatch.context() as patch:
        patch.setattr(github, "respond", unreadable_refs)
        await worker.advance_project(UUID(project["id"]))
    assert (await get(client, project, plan))["items"][0]["state"] == "preparing"
    assert not github.pulls
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert (await get(client, project, plan))["items"][0]["pipeline_run_id"]


async def test_exact_ref_in_successful_listing_recovers_initial_404(client, setup_work, monkeypatch):
    project, github, worker, _ = setup_work
    plan = await create(client, project)
    original = github.respond

    def missing_single_ref(request):
        if request.url.path == "/repos/owner/app/git/ref/heads/main":
            return httpx.Response(404)
        return original(request)

    with monkeypatch.context() as patch:
        patch.setattr(github, "respond", missing_single_ref)
        await worker.advance_project(UUID(project["id"]))
    assert (await get(client, project, plan))["items"][0]["pipeline_run_id"]
