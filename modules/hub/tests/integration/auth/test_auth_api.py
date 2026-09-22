"""Signing in for real: these tests remove the stand-in user the other suites run as."""

import bcrypt
import pytest
from app.auth import require_scheduler_or_user
from app.main import ensure_first_user
from app_layer_base.core.database.deps import get_session
from app_prebuilt_auth.user.deps import get_current_user, get_login_throttle
from app_prebuilt_auth.user.models import User
from sqlalchemy import select

from tests.utils.assertions import assert_status_code

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]

LOGIN = "/api/v1/users/login/"
REFRESH = "/api/v1/users/login/refresh"
PROTECTED = "/api/v1/connectors"
TRIGGER = "/api/v1/dispatchers/trigger"
OPERATOR = {"username": "operator@example.com", "password": "operator-password"}


@pytest.fixture(autouse=True)
async def real_auth(app, session):
    app.dependency_overrides.pop(get_current_user)
    app.dependency_overrides.pop(require_scheduler_or_user)
    get_login_throttle().reset()
    await ensure_first_user()
    yield
    get_login_throttle().reset()


@pytest.fixture(autouse=True)
async def request_sessions(client, app, session_maker):
    # The shared client fixture reuses one session. Authentication must observe
    # commits from login/startup through a fresh identity map on every request.
    async def fresh_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = fresh_session


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_the_operator_signs_in_and_the_api_needs_the_token(client, session):
    assert_status_code(await client.get(PROTECTED), 401)
    assert_status_code(await client.get(PROTECTED, headers=bearer("not-a-token")), 401)

    signed_in = await client.post(LOGIN, data=OPERATOR)

    assert_status_code(signed_in, 200)
    tokens = signed_in.json()
    assert tokens["token_type"] == "bearer" and tokens["expires_in"] > 0
    assert_status_code(await client.get(PROTECTED, headers=bearer(tokens["access_token"])), 200)
    # A refresh token is not an access token.
    assert_status_code(await client.get(PROTECTED, headers=bearer(tokens["refresh_token"])), 401)
    # The database holds a slow hash, never the password.
    operator = await session.scalar(select(User).where(User.email == OPERATOR["username"]))
    assert operator is not None and operator.is_superadmin
    assert operator.hashed_password.startswith("$argon2id$")


async def test_a_session_is_extended_by_its_refresh_token(client):
    tokens = (await client.post(LOGIN, data=OPERATOR)).json()

    renewed = await client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})

    assert_status_code(renewed, 200)
    assert_status_code(await client.get(PROTECTED, headers=bearer(renewed.json()["access_token"])), 200)
    assert_status_code(await client.post(REFRESH, json={"refresh_token": tokens["access_token"]}), 401)


async def test_bcrypt_login_persists_the_hash_before_refresh(client, session, session_maker):
    operator = await session.scalar(select(User).where(User.email == OPERATOR["username"]))
    operator.hashed_password = bcrypt.hashpw(OPERATOR["password"].encode(), bcrypt.gensalt(rounds=4)).decode()
    await session.commit()
    tokens = (await client.post(LOGIN, data=OPERATOR)).json()

    async with session_maker() as verification:
        persisted = await verification.get(User, operator.id)
        assert persisted.hashed_password.startswith("$argon2id$")
    assert_status_code(await client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]}), 200)


async def test_bootstrap_operator_profile_and_list_are_readable(client, session):
    tokens = (await client.post(LOGIN, data=OPERATOR)).json()
    operator = await session.scalar(select(User).where(User.email == OPERATOR["username"]))
    profile = await client.get(f"/api/v1/users/{operator.id}", headers=bearer(tokens["access_token"]))
    assert_status_code(profile, 200)
    assert profile.json()["lastname"] is None
    assert_status_code(await client.get("/api/v1/users/admin/", headers=bearer(tokens["access_token"])), 200)


async def test_inactive_operator_cannot_reuse_a_session(client, session, scheduler_key):
    tokens = (await client.post(LOGIN, data=OPERATOR)).json()
    operator = await session.scalar(select(User).where(User.email == OPERATOR["username"]))
    operator.is_active = False
    await session.commit()

    assert_status_code(await client.get(PROTECTED, headers=bearer(tokens["access_token"])), 401)
    assert_status_code(await client.post(TRIGGER, headers=bearer(tokens["access_token"])), 401)
    assert_status_code(await client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]}), 401)
    # Disabling the person does not stop the independent scheduler.
    assert_status_code(await client.post(TRIGGER, headers=scheduler_key), 200)


async def test_swagger_authorize_uses_the_real_login_endpoint(client):
    schema = (await client.get("/openapi.json")).json()
    token_url = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"]
    assert_status_code(await client.post(token_url, data=OPERATOR), 200)


async def test_repeated_failed_logins_lock_the_caller_out_and_tell_the_operator(client, monkeypatch):
    notices: list[str] = []

    async def capture(self, text: str, **kwargs):
        notices.append(text)
        return []

    monkeypatch.setattr("app.features.notifications.notifier.Notifier.send", capture)
    caller = {"X-Forwarded-For": "1.2.3.4, 203.0.113.7"}
    wrong = {**OPERATOR, "password": "guess"}

    for _ in range(5):
        assert_status_code(await client.post(LOGIN, data=wrong, headers=caller), 400)
    locked = await client.post(LOGIN, data=OPERATOR, headers=caller)

    assert_status_code(locked, 429)
    # The UI tells the operator how long to wait from this header.
    assert 0 < int(locked.headers["Retry-After"]) <= 300
    assert len(notices) == 1 and "203.0.113.x" in notices[0] and "203.0.113.7" not in notices[0]
    # The lockout follows the address the platform appended, not the one the client invented.
    spoofed = {"X-Forwarded-For": "9.9.9.9, 203.0.113.7"}
    assert_status_code(await client.post(LOGIN, data=OPERATOR, headers=spoofed), 429)
    assert_status_code(await client.post(LOGIN, data=OPERATOR, headers={"X-Forwarded-For": "198.51.100.9"}), 200)


async def test_the_scheduler_key_opens_the_trigger_and_nothing_else(client, scheduler_key):
    scheduler = scheduler_key

    assert_status_code(await client.post(TRIGGER, headers=scheduler), 200)
    assert_status_code(await client.get(PROTECTED, headers=scheduler), 401)
    assert_status_code(await client.post(TRIGGER, headers={"X-API-Key": "wrong"}), 401)
    assert_status_code(await client.post(TRIGGER), 401)

    tokens = (await client.post(LOGIN, data=OPERATOR)).json()
    # A person pressing "Trigger Dispatcher" in the UI.
    assert_status_code(await client.post(TRIGGER, headers=bearer(tokens["access_token"])), 200)


async def test_a_password_changed_in_the_secrets_replaces_the_old_one_at_startup(client, monkeypatch):
    from app_prebuilt_auth.user.config import get_auth_settings

    tokens = (await client.post(LOGIN, data=OPERATOR)).json()
    monkeypatch.setenv("FIRST_USER_PASSWORD", "rotated-password")
    get_auth_settings.cache_clear()
    try:
        await ensure_first_user()

        assert_status_code(await client.post(LOGIN, data=OPERATOR), 400)
        assert_status_code(await client.post(LOGIN, data={**OPERATOR, "password": "rotated-password"}), 200)
        # Sessions issued under the old password cannot be extended.
        assert_status_code(await client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]}), 401)
    finally:
        monkeypatch.undo()
        get_auth_settings.cache_clear()


ROOT = {"X-Root-API-Key": "root-test-credential-at-least-32-characters"}


@pytest.fixture
async def scheduler_key(client):
    machine = await client.post(
        "/api/v1/machines", headers=ROOT, json={"name": "cloud-scheduler", "scopes": ["autohub:dispatch"]}
    )
    assert machine.status_code == 201, machine.text
    key = await client.post(f"/api/v1/machines/{machine.json()['id']}/keys", headers=ROOT, json={"label": "deployment"})
    assert key.status_code == 201, key.text
    return {"X-API-Key": key.json()["key"]}


async def test_root_only_manages_keys_and_revocation_stops_scheduler(client, scheduler_key):
    assert_status_code(await client.post(TRIGGER, headers=ROOT), 401)
    assert_status_code(await client.get(PROTECTED, headers=ROOT), 401)
    assert_status_code(await client.get("/api/v1/users/admin/", headers=ROOT), 401)
    assert_status_code(await client.get("/api/v1/machines", headers=scheduler_key), 401)
    assert_status_code(await client.post(TRIGGER, headers=scheduler_key), 200)
    machine = (await client.get("/api/v1/machines", headers=ROOT)).json()[0]
    path = f"/api/v1/machines/{machine['id']}/keys"
    key = (await client.get(path, headers=ROOT)).json()[0]
    assert_status_code(await client.delete(f"{path}/{key['id']}", headers=ROOT), 200)
    assert_status_code(await client.post(TRIGGER, headers=scheduler_key), 401)


async def test_machine_needs_dispatch_scope_and_human_admin_can_manage_keys(client):
    tokens = (await client.post(LOGIN, data=OPERATOR)).json()
    human = bearer(tokens["access_token"])
    machine = await client.post("/api/v1/machines", headers=human, json={"name": "no-permission"})
    assert_status_code(machine, 201)
    key = (
        await client.post(f"/api/v1/machines/{machine.json()['id']}/keys", headers=ROOT, json={"label": "empty"})
    ).json()
    assert_status_code(await client.post(TRIGGER, headers={"X-API-Key": key["key"]}), 403)
    assert_status_code(
        await client.post("/api/v1/machines", headers=ROOT, json={"name": "bad", "scopes": ["planroot:agent"]}), 400
    )


async def test_google_login_is_optional_and_approval_is_required(client):
    from app.auth_settings import get_hub_auth_settings

    assert get_hub_auth_settings().REGISTRATION_REQUIRE_APPROVAL is True
    response = await client.get("/api/v1/auth/google/options")
    assert response.status_code == 200
    assert response.json() == {"enabled": False}
    assert (await client.get("/api/v1/auth/google/start")).status_code == 404


async def test_pending_and_suspended_accounts_cannot_use_hub_apis(client, session):
    from app_prebuilt_auth.user.config import get_auth_settings
    from app_prebuilt_auth.user.repos import UserRepository
    from app_prebuilt_auth.user.services import UserService

    user = User(firstname="Google", email="google@example.com", approval_status="approved")
    session.add(user)
    await session.commit()
    service = UserService(get_auth_settings(), UserRepository())
    token = service.create_access_token(user)
    user.approval_status = "pending"
    await session.commit()
    assert (await client.get(PROTECTED, headers=bearer(token))).status_code == 401
    assert (await client.get("/api/v1/users/admin/", headers=bearer(token))).status_code == 401
    user.approval_status = "approved"
    await session.commit()
    assert (await client.get(PROTECTED, headers=bearer(token))).status_code == 200
    assert (await client.get("/api/v1/users/admin/", headers=bearer(token))).status_code == 403
