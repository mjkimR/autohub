"""Untrusted CLI output can select safe guidance, never supply operator text or actions."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import checkout, diagnostics
from app.features.project_management.sdd.schemas import SddDiagnostic

pytestmark = pytest.mark.unit


def hostile(code: object = "SPEC_APPROVAL_KEY_IGNORED", level="WARNING"):
    return {
        "code": code,
        "level": level,
        "message": "secret-token /private/path",
        "advisory": {"action": "run secret-command", "retry": "SAFE", "target_files": ["/private/path"]},
    }


@pytest.mark.parametrize(
    "code", ["SPEC_APPROVAL_KEY_IGNORED", "secret-token", {"secret-token": True}, ["private-path"]]
)
def test_notices_only_select_catalog_values_and_are_bounded(code):
    rows = diagnostics.notices({"notices": [hostile(code)] * 1000})
    assert len(rows) == 1
    row = SddDiagnostic.model_validate(rows[0])
    assert row.severity == "warning" and row.retry == "never"
    assert "secret" not in row.model_dump_json() and "/private" not in row.model_dump_json()
    if code == "SPEC_APPROVAL_KEY_IGNORED":
        assert row.code == code and row.target_files == [".devkit/config.toml"]
        assert row.category == "repository" and "approval" in row.message
    else:
        assert row.code == "DEVKIT_NOTICE" and row.target_files == []


@pytest.mark.parametrize("payload", [None, [], {"notices": "private"}, {"notices": [None, [], 1]}])
def test_malformed_notice_lists_do_not_become_diagnostics(payload):
    assert diagnostics.notices(payload) == []


async def test_successful_subprocess_notices_are_collected_without_stderr(tmp_path, monkeypatch):
    process = AsyncMock(returncode=0)
    process.communicate.return_value = (json.dumps({"notices": [hostile()]}).encode(), b"secret stderr")
    monkeypatch.setattr(checkout.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    with diagnostics.capture() as rows:
        await checkout._command("devkit", cwd=tmp_path, env={}, allow_failure=False, devkit=True)
    assert [row["code"] for row in rows] == ["SPEC_APPROVAL_KEY_IGNORED"]
    assert "secret" not in json.dumps(rows)


@pytest.mark.parametrize(
    "payload",
    [
        {"error": hostile("RULES_RUN_FAILED")},
        {"errors": [hostile(["secret"])]},
        {"errors": {"code": "private"}},
        {"errors": ["private"]},
        ["private"],
    ],
)
async def test_error_diagnostics_never_leak_upstream_values(tmp_path, monkeypatch, payload):
    process = AsyncMock(returncode=2)
    process.communicate.return_value = (json.dumps(payload).encode(), b"secret stderr")
    monkeypatch.setattr(checkout.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    with pytest.raises(checkout.SddCommandError) as result:
        await checkout._command("devkit", cwd=tmp_path, env={}, allow_failure=False, devkit=True)
    rows = result.value.diagnostics
    assert len(rows) == 1 and rows[0]["severity"] == "error"
    assert "secret" not in json.dumps(rows) and "private" not in json.dumps(rows)
    assert rows[0]["code"] == (
        "RULES_RUN_FAILED" if isinstance(payload, dict) and "error" in payload else "COMMAND_FAILED"
    )


@pytest.mark.parametrize(
    "code,category",
    [
        ("SDD_RUNTIME_UNAVAILABLE", "runtime"),
        ("SDD_PROFILE_INVALID", "runtime"),
        ("SDD_BUNDLES_MISSING", "runtime"),
        ("SDD_RECEIPT_MISSING", "repository"),
    ],
)
def test_host_failures_have_safe_actionable_diagnostics(code, category):
    rows = diagnostics.failure(ProjectError(422, "secret details", code=code))
    assert rows[0]["code"] == code and rows[0]["category"] == category
    assert "secret" not in json.dumps(rows) and rows[0]["action"]


async def test_diagnostic_capture_is_task_local_and_nested_reads_share_one_evaluation():
    entered, observed = asyncio.Event(), asyncio.Event()

    async def first():
        with diagnostics.capture() as rows:
            diagnostics.collect({"notices": [hostile()]})
            with diagnostics.capture() as nested:
                assert nested is rows
            entered.set()
            await observed.wait()
        return rows

    async def second():
        await entered.wait()
        with diagnostics.capture() as rows:
            assert rows == []
            diagnostics.collect({"notices": [hostile("POST_SYNC_NOTICE", "NOTICE")]})
            observed.set()
        return rows

    first_rows, second_rows = await asyncio.gather(first(), second())
    assert [row["code"] for row in first_rows] == ["SPEC_APPROVAL_KEY_IGNORED"]
    assert [row["code"] for row in second_rows] == ["POST_SYNC_NOTICE"]
    with diagnostics.capture() as clean:
        assert clean == []


def test_failure_is_not_lost_when_prior_notices_exhaust_the_budget():
    codes = list(diagnostics.CLI_FIXES)
    assert len(codes) > diagnostics.LIMIT
    prior = diagnostics.notices({"notices": [hostile(code) for code in codes]})
    assert len(prior) == diagnostics.LIMIT
    error = diagnostics.diagnostic("RULES_RUN_FAILED")
    retained = diagnostics.merge(prior, [error])
    assert len(retained) == diagnostics.LIMIT and retained[0] == error
