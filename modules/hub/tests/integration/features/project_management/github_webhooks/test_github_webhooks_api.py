import hashlib
import hmac
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.common.config import get_github_webhook_config
from app.features.project_management.github_webhooks.models import GitHubWebhookDelivery
from app.features.project_management.github_webhooks.usecases import (
    AUTO_RUN_TRIGGER,
    GitHubWebhookUseCase,
    _extract_trigger_text,
)
from app.features.project_management.pipeline_runs.schemas import EnrollPullRequest

pytestmark = pytest.mark.integration


def _headers(body: bytes, delivery: str = "delivery-1", event: str = "ping") -> dict[str, str]:
    secret = b"webhook-test-secret"
    return {
        "X-GitHub-Delivery": delivery,
        "X-GitHub-Event": event,
        "X-Hub-Signature-256": "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest(),
        "Content-Type": "application/json",
    }


async def test_github_webhook_verifies_signature_and_deduplicates(client, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhook-test-secret")
    get_github_webhook_config.cache_clear()
    body = b'{"repository":{"full_name":"owner/repository"}}'

    payload = {"repository": {"full_name": "owner/repository"}}
    response = await client.post("/api/github/webhooks", json=payload, headers=_headers(body))
    duplicate = await client.post("/api/github/webhooks", json=payload, headers=_headers(body))

    assert response.request.content == body
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert duplicate.status_code == 202
    assert duplicate.json() == {"status": "duplicate"}
    get_github_webhook_config.cache_clear()


async def test_github_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhook-test-secret")
    get_github_webhook_config.cache_clear()
    body = b"{}"
    headers = _headers(body)
    headers["X-Hub-Signature-256"] = "sha256=not-valid"

    response = await client.post("/api/github/webhooks", json={}, headers=headers)

    assert response.status_code == 401
    get_github_webhook_config.cache_clear()


def test_auto_run_regex_matching():
    assert AUTO_RUN_TRIGGER.search("@auto-run")
    assert AUTO_RUN_TRIGGER.search("@Auto-Run please do this")
    assert AUTO_RUN_TRIGGER.search("Please review this PR @AUTO-RUN\nThanks!")
    assert not AUTO_RUN_TRIGGER.search("@auto-running")
    assert not AUTO_RUN_TRIGGER.search("no trigger here")


def test_auto_run_names_a_catalog_by_key_or_kind():
    def named_catalog(text: str) -> str | None:
        match = AUTO_RUN_TRIGGER.search(text)
        assert match is not None
        return match.group("catalog")

    assert named_catalog("@auto-run please") is None
    assert named_catalog("@auto-run:codex please") == "codex"
    assert named_catalog("ship it @auto-run:personal-jules") == "personal-jules"
    # A bare colon designates nothing.
    assert named_catalog("@auto-run: now") is None


def test_extract_trigger_text():
    # PR opened with body
    assert (
        _extract_trigger_text("pull_request", {"action": "opened", "pull_request": {"body": "hello @auto-run"}})
        == "hello @auto-run"
    )
    # PR reopened with body
    assert (
        _extract_trigger_text("pull_request", {"action": "reopened", "pull_request": {"body": "recheck @auto-run"}})
        == "recheck @auto-run"
    )
    # PR closed (ignored)
    assert _extract_trigger_text("pull_request", {"action": "closed", "pull_request": {"body": "done"}}) is None

    # Issue comment on PR
    pr_comment = {
        "action": "created",
        "issue": {"number": 12, "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/12"}},
        "comment": {"body": "@auto-run run tests"},
    }
    assert _extract_trigger_text("issue_comment", pr_comment) == "@auto-run run tests"

    # Issue comment on regular issue (not PR)
    issue_comment = {
        "action": "created",
        "issue": {"number": 12},
        "comment": {"body": "@auto-run run tests"},
    }
    assert _extract_trigger_text("issue_comment", issue_comment) is None

    # Deleted comment
    deleted_comment = {
        "action": "deleted",
        "issue": {"number": 12, "pull_request": {}},
        "comment": {"body": "@auto-run"},
    }
    assert _extract_trigger_text("issue_comment", deleted_comment) is None


async def test_webhook_pr_opened_with_auto_run_enrolls_and_advances():
    repo = MagicMock()
    runs = MagicMock()
    lifecycle = MagicMock()
    lifecycle.observer = MagicMock()

    project = MagicMock(id=uuid4(), enabled=True)
    repo.project_for_repository = AsyncMock(return_value=project)
    runs.get_active_for_pull = AsyncMock(return_value=None)

    new_run = MagicMock(id=uuid4())
    lifecycle.enroll = AsyncMock(return_value=new_run)
    lifecycle.manual_advance = AsyncMock()

    webhook = GitHubWebhookUseCase(repo, runs, lifecycle)
    webhook._finish = AsyncMock()

    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/app"},
        "pull_request": {"number": 42, "body": "Feature description\n\n@auto-run please implement"},
    }
    await webhook.process("del-1", payload, event="pull_request")

    lifecycle.enroll.assert_awaited_once_with(project.id, EnrollPullRequest(pull_number=42))
    lifecycle.manual_advance.assert_awaited_once_with(new_run.id, lifecycle.observer)
    webhook._finish.assert_awaited_once_with("del-1", "processed")


def make_webhook(*, enroll):
    repo = MagicMock()
    runs = MagicMock()
    lifecycle = MagicMock()
    lifecycle.observer = MagicMock()
    repo.project_for_repository = AsyncMock(return_value=MagicMock(id=uuid4(), enabled=True))
    runs.get_active_for_pull = AsyncMock(return_value=None)
    lifecycle.enroll = enroll
    lifecycle.manual_advance = AsyncMock()
    webhook = GitHubWebhookUseCase(repo, runs, lifecycle)
    finish = AsyncMock()
    webhook._finish = finish
    return webhook, lifecycle, finish


async def test_webhook_trigger_passes_the_named_catalog_to_enrollment():
    new_run = MagicMock(id=uuid4())
    webhook, lifecycle, finish = make_webhook(enroll=AsyncMock(return_value=new_run))
    payload = {
        "action": "created",
        "repository": {"full_name": "owner/app"},
        "issue": {"number": 15, "pull_request": {"html_url": "https://..."}},
        "comment": {"body": "@auto-run:codex take this one"},
    }

    await webhook.process("del-2", payload, event="issue_comment")

    project_id = lifecycle.enroll.await_args.args[0]
    lifecycle.enroll.assert_awaited_once_with(project_id, EnrollPullRequest(pull_number=15, catalog="codex"))
    finish.assert_awaited_once_with("del-2", "processed")


async def test_webhook_records_why_a_trigger_did_not_enroll():
    from app.features.project_management.projects.errors import ProjectError

    webhook, lifecycle, finish = make_webhook(
        enroll=AsyncMock(side_effect=ProjectError(422, "AI catalog 'personal-jules' cannot deliver pull request work"))
    )
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/app"},
        "pull_request": {"number": 42, "body": "@auto-run:jules"},
    }

    await webhook.process("del-3", payload, event="pull_request")

    lifecycle.manual_advance.assert_not_awaited()
    finish.assert_awaited_once_with(
        "del-3", "processed", "Enrollment skipped: AI catalog 'personal-jules' cannot deliver pull request work"
    )


async def test_webhook_notes_a_deferred_first_dispatch_after_enrolling():
    from app.features.project_management.projects.errors import ProjectError

    webhook, lifecycle, finish = make_webhook(enroll=AsyncMock(return_value=MagicMock(id=uuid4())))
    lifecycle.manual_advance = AsyncMock(side_effect=ProjectError(409, "AI catalog is quota-blocked"))
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/app"},
        "pull_request": {"number": 42, "body": "@auto-run"},
    }

    await webhook.process("del-4", payload, event="pull_request")

    finish.assert_awaited_once_with(
        "del-4", "processed", "Enrolled; first dispatch deferred: AI catalog is quota-blocked"
    )


async def test_webhook_pr_opened_without_auto_run_is_ignored():
    repo = MagicMock()
    runs = MagicMock()
    lifecycle = MagicMock()

    project = MagicMock(id=uuid4(), enabled=True)
    repo.project_for_repository = AsyncMock(return_value=project)
    runs.get_active_for_pull = AsyncMock(return_value=None)
    lifecycle.enroll = AsyncMock()
    lifecycle.manual_advance = AsyncMock()

    webhook = GitHubWebhookUseCase(repo, runs, lifecycle)
    webhook._finish = AsyncMock()

    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/app"},
        "pull_request": {"number": 42, "body": "Normal human PR without bot mention"},
    }
    await webhook.process("del-2", payload, event="pull_request")

    lifecycle.enroll.assert_not_awaited()
    lifecycle.manual_advance.assert_not_awaited()
    webhook._finish.assert_awaited_once_with("del-2", "processed")


async def test_webhook_comment_with_auto_run_enrolls_when_no_active_run():
    repo = MagicMock()
    runs = MagicMock()
    lifecycle = MagicMock()
    lifecycle.observer = MagicMock()

    project = MagicMock(id=uuid4(), enabled=True)
    repo.project_for_repository = AsyncMock(return_value=project)
    runs.get_active_for_pull = AsyncMock(return_value=None)

    new_run = MagicMock(id=uuid4())
    lifecycle.enroll = AsyncMock(return_value=new_run)
    lifecycle.manual_advance = AsyncMock()

    webhook = GitHubWebhookUseCase(repo, runs, lifecycle)
    webhook._finish = AsyncMock()

    payload = {
        "action": "created",
        "repository": {"full_name": "owner/app"},
        "issue": {"number": 15, "pull_request": {"html_url": "https://..."}},
        "comment": {"body": "@auto-run start this task"},
    }
    await webhook.process("del-3", payload, event="issue_comment")

    lifecycle.enroll.assert_awaited_once_with(project.id, EnrollPullRequest(pull_number=15))
    lifecycle.manual_advance.assert_awaited_once_with(new_run.id, lifecycle.observer)
    webhook._finish.assert_awaited_once_with("del-3", "processed")


async def test_webhook_comment_with_auto_run_advances_existing_active_run():
    repo = MagicMock()
    runs = MagicMock()
    lifecycle = MagicMock()
    lifecycle.observer = MagicMock()

    project = MagicMock(id=uuid4(), enabled=True)
    existing_run = MagicMock(id=uuid4())
    repo.project_for_repository = AsyncMock(return_value=project)
    runs.get_active_for_pull = AsyncMock(return_value=existing_run)

    lifecycle.enroll = AsyncMock()
    lifecycle.manual_advance = AsyncMock()

    webhook = GitHubWebhookUseCase(repo, runs, lifecycle)
    webhook._finish = AsyncMock()

    payload = {
        "action": "created",
        "repository": {"full_name": "owner/app"},
        "issue": {"number": 15, "pull_request": {"html_url": "https://..."}},
        "comment": {"body": "@auto-run retry"},
    }
    await webhook.process("del-4", payload, event="issue_comment")

    lifecycle.enroll.assert_not_awaited()
    lifecycle.manual_advance.assert_awaited_once_with(existing_run.id, lifecycle.observer)
    webhook._finish.assert_awaited_once_with("del-4", "processed")


async def test_out_of_order_webhooks_route_each_pull_request_to_its_own_active_run():
    """A repository can have concurrent runs; delivery order must not cross them."""
    repo = MagicMock()
    runs = MagicMock()
    lifecycle = MagicMock()
    lifecycle.observer = MagicMock()
    project = MagicMock(id=uuid4(), enabled=True)
    first, second = MagicMock(id=uuid4()), MagicMock(id=uuid4())
    repo.project_for_repository = AsyncMock(return_value=project)
    runs.get_active_for_pull = AsyncMock(
        side_effect=lambda _session, _project_id, number: {7: first, 8: second}[number]
    )
    lifecycle.manual_advance = AsyncMock()

    webhook = GitHubWebhookUseCase(repo, runs, lifecycle)
    webhook._finish = AsyncMock()
    # The later PR's workflow event arrives before the earlier PR's push event.
    await webhook.process(
        "workflow-8",
        {"repository": {"full_name": "owner/app"}, "workflow_run": {"pull_requests": [{"number": 8}]}},
        event="workflow_run",
    )
    await webhook.process(
        "push-7",
        {"repository": {"full_name": "owner/app"}, "pull_request": {"number": 7}},
        event="pull_request",
    )

    assert lifecycle.manual_advance.await_args_list[0].args == (second.id, lifecycle.observer)
    assert lifecycle.manual_advance.await_args_list[1].args == (first.id, lifecycle.observer)
    assert webhook._finish.await_args_list[0].args == ("workflow-8", "processed")
    assert webhook._finish.await_args_list[1].args == ("push-7", "processed")


async def test_failed_webhook_processing_is_acknowledged_for_polling_recovery():
    """A transient webhook failure must not be retried as a duplicate write."""
    repo = MagicMock()
    runs = MagicMock()
    lifecycle = MagicMock()
    lifecycle.observer = MagicMock()
    project = MagicMock(id=uuid4(), enabled=True)
    run = MagicMock(id=uuid4())
    repo.project_for_repository = AsyncMock(return_value=project)
    runs.get_active_for_pull = AsyncMock(return_value=run)
    lifecycle.manual_advance = AsyncMock(side_effect=RuntimeError("temporary GitHub outage"))

    webhook = GitHubWebhookUseCase(repo, runs, lifecycle)
    webhook._finish = AsyncMock()
    await webhook.process(
        "failed-advance",
        {"repository": {"full_name": "owner/app"}, "pull_request": {"number": 7}},
        event="pull_request",
    )

    webhook._finish.assert_awaited_once_with("failed-advance", "failed", "Webhook processing failed")


async def test_the_delivery_log_lists_deliveries_and_finds_the_noteworthy_ones(client, session):
    from app_testing_base import utc_now

    def delivery(delivery_id: str, minutes_ago: int, **fields) -> GitHubWebhookDelivery:
        return GitHubWebhookDelivery(
            delivery_id=delivery_id,
            event="issue_comment",
            repository="owner/app",
            payload_digest="0" * 64,
            created_at=utc_now() - timedelta(minutes=minutes_ago),
            **fields,
        )

    session.add_all(
        [
            delivery("ordinary", 3, status="processed", attempts=1),
            delivery(
                "skipped-trigger",
                2,
                status="processed",
                attempts=1,
                pull_number=7,
                auto_run=True,
                requested_catalog="jules",
                failure_detail="Enrollment skipped: AI catalog 'jules' cannot deliver pull request work",
            ),
            delivery("broken", 1, status="failed", attempts=2),
        ]
    )
    await session.commit()
    url = "/api/v1/github-webhook-deliveries"

    everything = await client.get(url)
    assert everything.status_code == 200
    assert [item["delivery_id"] for item in everything.json()["items"]] == ["broken", "skipped-trigger", "ordinary"]
    assert everything.json()["total_count"] == 3
    assert "payload_digest" not in everything.json()["items"][0]

    noteworthy = (await client.get(url, params={"noteworthy": True})).json()
    assert [item["delivery_id"] for item in noteworthy["items"]] == ["broken", "skipped-trigger"]
    trigger = noteworthy["items"][1]
    assert (trigger["pull_number"], trigger["auto_run"], trigger["requested_catalog"]) == (7, True, "jules")
    assert trigger["failure_detail"].startswith("Enrollment skipped")

    failed = (await client.get(url, params={"status": "failed", "repository": "Owner/App"})).json()
    assert ([item["delivery_id"] for item in failed["items"]], failed["total_count"]) == (["broken"], 1)
    assert (await client.get(url, params={"status": "lost"})).status_code == 422
