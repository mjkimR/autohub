from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from app.features.notifications.decision_models import DecisionNoticeAttempt
from app.features.notifications.decision_repo import DecisionNoticeRepository
from app.features.notifications.decision_transport import send_decision_message
from app.features.notifications.decision_worker import DecisionNoticeWorker
from app.features.project_management.pipeline_runs.models import RunQuestion
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import select

from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios
from tests.integration.features.project_management.pipeline_runs.test_interactions import ask

project = scenarios.project
github = scenarios.github
enroll = scenarios.enroll
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
ROOT = "/api/v1/notification-channels"


def settings(**extra):
    return {
        "request_id": str(uuid4()),
        "expected_revision": 0,
        "expected_destination_generation": 0,
        "enabled": True,
        "project_scope": "all",
        "project_ids": [],
        "kinds": ["run-question"],
        "mode": "immediate",
        "review_origin": "https://hub.example",
        "trusted_destination": True,
        **extra,
    }


async def setup_decision(client, project):
    run = (await enroll(client, project)).json()
    await ask(client, f"/api/v1/pipeline-runs/{run['id']}")
    return run


async def test_defaults_rotation_replay_and_actor_outcome(client, channel):
    root = f"{ROOT}/{channel['id']}"
    initial = (await client.get(root + "/decision-subscription")).json()
    assert initial["revision"] == 0 and not initial["settings"]["enabled"]
    command = settings()
    first = await client.put(root + "/decision-subscription", json=command)
    assert first.status_code == 200, first.text
    assert first.json()["record_state"] == "recorded"
    await client.patch(root, json={"chat_id": "rotated"})
    replay = await client.put(root + "/decision-subscription", json=command)
    assert replay.status_code == 200
    assert replay.json()["result"]["revision"] == 1
    assert replay.json()["current"]["destination_generation"] == 1
    assert not replay.json()["current"]["settings"]["enabled"]
    changed = await client.put(root + "/decision-subscription", json={**command, "mode": "digest"})
    assert changed.status_code == 409
    outcome = await client.get(
        root + f"/decision-requests/{command['request_id']}", params={"operation": "subscription"}
    )
    assert outcome.json()["result"] == first.json()["result"]
    unknown = await client.get(root + f"/decision-requests/{uuid4()}", params={"operation": "subscription"})
    assert unknown.json()["record_state"] == "unknown"


async def test_revision_zero_destination_and_strict_input(client, channel):
    root = f"{ROOT}/{channel['id']}"
    await client.patch(root, json={"bot_token": "fresh-token"})
    assert (await client.put(root + "/decision-subscription", json=settings())).status_code == 409
    for patch in [
        {"review_origin": "https://evil.example/path"},
        {"actor": "other"},
        {"trusted_destination": False},
        {"kinds": []},
    ]:
        assert (await client.put(root + "/decision-subscription", json=settings(**patch))).status_code == 422


async def test_send_dedupe_unknown_and_exact_resend(
    client, channel, project, github, session, monkeypatch, credential_key_provider
):
    await setup_decision(client, project)
    root = f"{ROOT}/{channel['id']}"
    assert (await client.put(root + "/decision-subscription", json=settings())).status_code == 200
    sends = []

    async def send(*args):
        sends.append(args[-1])
        return "unknown", "transport-unconfirmed"

    from app.features.configuration.connectors.crypto import ConnectorCredentialCipher
    from app.features.notifications.repos import NotificationChannelRepository
    from app.features.notifications.services import NotificationChannelService

    worker = DecisionNoticeWorker(
        NotificationChannelService(NotificationChannelRepository(), ConnectorCredentialCipher(credential_key_provider)),
        transport=send,
    )
    id = await worker.collect(UUID(channel["id"]))
    assert id
    await worker.deliver(id)
    assert len(sends) == 1 and "question" not in sends[0].lower().replace("run-question", "")
    assert "decision_key=" in sends[0] and len(sends[0]) <= 3500
    assert await worker.collect(UUID(channel["id"])) is None
    history = (await client.get(root + "/decision-notices")).json()
    [notice] = history["items"]
    assert notice["state"] == "unknown"
    monkeypatch.setattr(DecisionNoticeWorker, "deliver", lambda *args: _nothing())
    data = {"request_id": str(uuid4()), "expected_revision": 1, "expected_destination_generation": 0}
    assert (await client.post(root + f"/decision-notices/{notice['id']}/resend", json=data)).status_code == 409
    data["acknowledge_possible_duplicate"] = True
    first = await client.post(root + f"/decision-notices/{notice['id']}/resend", json=data)
    replay = await client.post(root + f"/decision-notices/{notice['id']}/resend", json=data)
    assert first.status_code == replay.status_code == 200
    assert first.json()["result"] == replay.json()["result"]
    assert len(list(await session.scalars(select(DecisionNoticeAttempt)))) == 2


async def _nothing():
    pass


async def test_digest_due_stale_suppression_and_lease(client, channel, project, github, session):
    await setup_decision(client, project)
    root = f"{ROOT}/{channel['id']}"
    await client.put(root + "/decision-subscription", json=settings(mode="digest"))
    worker = DecisionNoticeWorker()
    assert await worker.collect(UUID(channel["id"])) is None
    from app.features.notifications.decision_models import DecisionSubscription

    sub = await session.get(DecisionSubscription, UUID(channel["id"]), populate_existing=True)
    sub.digest_since = get_current_utc_time() - timedelta(minutes=16)
    await session.commit()
    id = await worker.collect(UUID(channel["id"]))
    assert id
    attempt = await session.get(DecisionNoticeAttempt, id, populate_existing=True)
    attempt.lease_expires_at = get_current_utc_time() - timedelta(seconds=1)
    await session.commit()
    assert await worker.collect(UUID(channel["id"])) is None
    session.expire_all()
    assert (await session.get(DecisionNoticeAttempt, id)).state == "unknown"
    notice = (await client.get(root + "/decision-notices")).json()["items"][0]
    assert notice["state"] == "unknown"


async def test_exact_selection_late_page_and_no_provider_calls(client, project, github, session):
    await setup_decision(client, project)
    [entry] = (await client.get("/api/v1/pipeline-runs/decisions")).json()["items"]
    github.paths.clear()
    selected = await client.get(
        "/api/v1/pipeline-runs/decisions/selection", params={"key": entry["key"], "fingerprint": entry["fingerprint"]}
    )
    assert selected.status_code == 200 and selected.json() == entry
    assert not github.paths
    assert (
        await client.get(
            "/api/v1/pipeline-runs/decisions/selection", params={"key": entry["key"], "fingerprint": "a" * 64}
        )
    ).status_code == 409
    assert (
        await client.get(
            "/api/v1/pipeline-runs/decisions/selection", params={"key": "missing", "fingerprint": "a" * 64}
        )
    ).status_code == 404


@pytest.mark.parametrize("response,expected", [(200, "accepted"), (400, "failed"), (500, "unknown")])
async def test_transport_classification_is_safe(response, expected):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(response, json={"ok": response == 200, "description": "secret"})
        )
    ) as client:
        state, detail = await send_decision_message(client, "token-secret", "chat", "text")
    assert state == expected and "secret" not in str(detail)


async def test_concurrent_admission_channel_lock_postgres(client, channel, project, github, session, monkeypatch):
    if session.bind.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    import asyncio

    await setup_decision(client, project)
    root = f"{ROOT}/{channel['id']}"
    await client.put(root + "/decision-subscription", json=settings())
    original = DecisionNoticeRepository.channel
    arrived = 0
    barrier = asyncio.Event()

    async def channel_lock(self, *args, **kwargs):
        nonlocal arrived
        arrived += 1
        if arrived == 2:
            barrier.set()
        await asyncio.wait_for(barrier.wait(), 5)
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(DecisionNoticeRepository, "channel", channel_lock)
    results = await asyncio.gather(*(DecisionNoticeWorker().collect(UUID(channel["id"])) for _ in range(2)))
    assert sum(id is not None for id in results) == 1
    assert len(list(await session.scalars(select(DecisionNoticeAttempt)))) == 1


async def test_late_lease_result_cannot_overwrite_unknown(
    client, channel, project, github, session, credential_key_provider
):
    await setup_decision(client, project)
    root = f"{ROOT}/{channel['id']}"
    await client.put(root + "/decision-subscription", json=settings())
    from app.features.configuration.connectors.crypto import ConnectorCredentialCipher
    from app.features.notifications.repos import NotificationChannelRepository
    from app.features.notifications.services import NotificationChannelService
    from app_layer_base.core.database.transaction import AsyncTransaction

    async def slow_send(*args):
        async with AsyncTransaction() as tx:
            row = await tx.get(DecisionNoticeAttempt, id)
            assert row is not None
            row.lease_expires_at = get_current_utc_time() - timedelta(seconds=1)
        return "accepted", None

    worker = DecisionNoticeWorker(
        NotificationChannelService(NotificationChannelRepository(), ConnectorCredentialCipher(credential_key_provider)),
        slow_send,
    )
    id = await worker.collect(UUID(channel["id"]))
    await worker.deliver(id)
    await worker.collect(UUID(channel["id"]))
    session.expire_all()
    assert (await session.get(DecisionNoticeAttempt, id)).state == "unknown"


async def test_message_count_character_budget_and_pending_overflow(client, channel, project, github, session):
    run = await setup_decision(client, project)
    for i in range(12):
        session.add(
            RunQuestion(
                id=uuid4(),
                pipeline_run_id=UUID(run["id"]),
                head_sha="c" * 40,
                question=f"private question {i}",
                actor="test",
                source="operator",
                state="open",
            )
        )
    await session.commit()
    root = f"{ROOT}/{channel['id']}"
    await client.put(root + "/decision-subscription", json=settings())
    worker = DecisionNoticeWorker()
    first = await worker.collect(UUID(channel["id"]))
    attempt = await session.get(DecisionNoticeAttempt, first, populate_existing=True)
    assert attempt is not None
    assert 0 < len(attempt.notice_ids) <= 10 and len(attempt.message) <= 3500
    assert "private question" not in attempt.message
    assert attempt.message.count("decision_key=") == len(attempt.notice_ids)
    second = await worker.collect(UUID(channel["id"]))
    assert second and second != first


async def test_subscription_receipt_failure_rolls_back_settings(client, channel, session):
    from app.features.notifications.decision_models import DecisionNoticeRequest, DecisionSubscription
    from sqlalchemy import event

    def refuse(*args):
        raise RuntimeError("receipt unavailable")

    event.listen(DecisionNoticeRequest, "before_insert", refuse)
    try:
        with pytest.raises(RuntimeError, match="receipt unavailable"):
            await client.put(f"{ROOT}/{channel['id']}/decision-subscription", json=settings())
    finally:
        event.remove(DecisionNoticeRequest, "before_insert", refuse)
    session.expire_all()
    assert await session.get(DecisionSubscription, UUID(channel["id"])) is None


async def test_disabled_subscription_baseline_then_one_matching_admission(client, channel, project, github):
    await setup_decision(client, project)
    worker = DecisionNoticeWorker()
    assert await worker.collect(UUID(channel["id"])) is None
    root = f"{ROOT}/{channel['id']}"
    assert (await client.put(root + "/decision-subscription", json=settings())).status_code == 200
    assert await worker.collect(UUID(channel["id"])) is not None
    assert await worker.collect(UUID(channel["id"])) is None


@pytest.mark.parametrize("exclusion", ["kind", "project"])
async def test_pending_digest_generation_recovers_after_filter_restoration(
    client, channel, project, github, session, exclusion
):
    await setup_decision(client, project)
    root = f"{ROOT}/{channel['id']}"
    original = settings(mode="digest")
    await client.put(root + "/decision-subscription", json=original)
    worker = DecisionNoticeWorker()
    assert await worker.collect(UUID(channel["id"])) is None
    excluded = (
        settings(expected_revision=1, mode="digest", kinds=["native-workflow"])
        if exclusion == "kind"
        else settings(expected_revision=1, mode="digest", project_scope="selected", project_ids=[str(project["id"])])
    )
    if exclusion == "project":
        # A second real project is not necessary: temporarily remove the entry's project from an all-project subscription by selecting an accessible other project.
        from app.features.project_management.projects.models import Project

        other = Project(name="Other project", github_repository="other/app")
        session.add(other)
        await session.commit()
        excluded["project_ids"] = [str(other.id)]
    assert (await client.put(root + "/decision-subscription", json=excluded)).status_code == 200
    assert await worker.collect(UUID(channel["id"])) is None
    restored = settings(expected_revision=2, mode="immediate")
    assert (await client.put(root + "/decision-subscription", json=restored)).status_code == 200
    assert await worker.collect(UUID(channel["id"])) is not None
