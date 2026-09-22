"""Provisioning preserves revocation and cleans up a failed one-time secret write."""

import importlib.util
import json
from email.message import Message
from io import BytesIO
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock
from urllib.request import HTTPSHandler
from urllib.response import addinfourl

import pytest

spec = importlib.util.spec_from_file_location(
    "scheduler_provision", Path(__file__).resolve().parents[5] / "scripts/provision-scheduler.py"
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

MACHINE = {"id": "m1", "name": "hub-scheduler", "is_active": True, "scopes": ["autohub:dispatch"]}
KEY = {"id": "abcd", "revoked_at": None, "expires_at": None}
SAVED = {"machine_id": "m1", "key_id": "abcd", "key": "ak_abcd_test-secret"}


class TransportResponse(addinfourl):
    msg = "Test response"


def test_redeployment_reuses_the_saved_credential_without_issuing_or_writing():
    api = Mock(side_effect=[[MACHINE], [KEY]])
    save = Mock()
    result = module.provision(api, lambda: SAVED, save, "hub-scheduler")
    assert result == SAVED
    assert [call.args[0] for call in api.call_args_list] == ["GET", "GET"]
    save.assert_not_called()


@pytest.mark.parametrize(
    "key", [{**KEY, "revoked_at": "2026-01-01T00:00:00Z"}, {**KEY, "expires_at": "2000-01-01T00:00:00Z"}]
)
def test_redeployment_never_replaces_a_revoked_or_expired_key(key):
    api = Mock(side_effect=[[MACHINE], [key]])
    save = Mock()
    with pytest.raises(RuntimeError, match="rotate it explicitly"):
        module.provision(api, lambda: SAVED, save, "hub-scheduler")
    save.assert_not_called()
    assert len(api.call_args_list) == 2


def test_failed_secret_write_revokes_the_new_key():
    issued = {**KEY, "key": SAVED["key"]}
    api = Mock(side_effect=[[MACHINE], [], issued, KEY])
    save = Mock(side_effect=RuntimeError("Do not expose this secret payload"))
    with pytest.raises(RuntimeError, match="newly issued key was revoked") as error:
        module.provision(api, lambda: None, save, "hub-scheduler")
    assert "payload" not in str(error.value)
    assert api.call_args_list[-1].args == ("DELETE", "/machines/m1/keys/abcd")


@pytest.mark.parametrize("key", [KEY, {**KEY, "revoked_at": "2026-01-01T00:00:00Z"}])
def test_missing_secret_with_existing_key_requires_manual_reconciliation(key):
    api = Mock(side_effect=[[MACHINE], [key]])
    with pytest.raises(RuntimeError, match="orphaned"):
        module.provision(api, lambda: None, Mock(), "hub-scheduler")
    assert len(api.call_args_list) == 2


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_management_redirects_never_forward_the_root_credential(monkeypatch, status):
    visited = []

    def transport(self, request):
        visited.append(request.full_url)
        assert request.get_header("X-root-api-key") == "test-root"
        headers = Message()
        headers["Location"] = "https://other.example/machines"
        return TransportResponse(BytesIO(b"[]"), headers, request.full_url, status)

    monkeypatch.setattr(HTTPSHandler, "https_open", transport)
    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        module.management_request("https://hub.example", "test-root", "GET", "/machines")
    assert visited == ["https://hub.example/api/v1/machines"]


def test_management_success_returns_the_issued_key_without_printing(monkeypatch, capsys):
    def transport(self, request):
        assert request.method == "POST"
        assert request.data == b'{"label": "scheduler"}'
        return TransportResponse(BytesIO(b'{"key":"test-one-time-secret"}'), Message(), request.full_url, 201)

    monkeypatch.setattr(HTTPSHandler, "https_open", transport)
    result = module.management_request(
        "https://hub.example", "test-root", "POST", "/machines/m1/keys", {"label": "scheduler"}
    )
    assert result == {"key": "test-one-time-secret"}
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("schedule", [None, "*/5 * * * *"])
def test_cli_reuses_machine_key_and_honors_configured_tick(monkeypatch, capsys, schedule):
    commands = []

    def cloud(command, **kwargs):
        commands.append(command)
        if command[1:4] == ["secrets", "versions", "access"]:
            value = {"APP_API_KEY_ROOT_KEY": "management-root"} if "--secret=autohub-secrets" in command else SAVED
        elif command[1:3] == ["secrets", "list"]:
            value = [{"name": "projects/p/secrets/hub-scheduler-credential"}]
        elif command[1:4] == ["scheduler", "jobs", "list"]:
            value = [{"name": "projects/p/locations/r/jobs/hub-dispatcher-tick"}]
        else:
            assert command[1:5] == ["scheduler", "jobs", "update", "http"]
            value = {}
        return CompletedProcess(command, 0, json.dumps(value), "")

    argv = [
        "provision-scheduler.py",
        "--project",
        "p",
        "--region",
        "r",
        "--service",
        "hub",
        "--url",
        "https://hub.example",
    ]
    if schedule:
        argv += ["--schedule", schedule]
    monkeypatch.setattr("sys.argv", argv)
    monkeypatch.setattr(module.subprocess, "run", cloud)
    api = Mock(side_effect=[[MACHINE], [KEY]])
    monkeypatch.setattr(module, "management_request", api)
    module.main()

    update = commands[-1]
    assert f"--schedule={schedule or '* * * * *'}" in update
    assert f"--update-headers=X-API-Key={SAVED['key']}" in update
    assert "--remove-headers=X-Scheduler-Key,X-Root-API-Key,Authorization" in update
    assert "--uri=https://hub.example/api/v1/dispatchers/trigger" in update
    assert "management-root" not in " ".join(update)
    assert [call.args[2] for call in api.call_args_list] == ["GET", "GET"]
    output = capsys.readouterr()
    assert SAVED["key"] not in output.out + output.err
    assert "management-root" not in output.out + output.err
