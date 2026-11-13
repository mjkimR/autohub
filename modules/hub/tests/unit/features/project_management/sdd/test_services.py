from pathlib import Path

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import services
from app.features.project_management.sdd.checkout import SddCommandError

pytestmark = pytest.mark.unit
SPEC = "specs/2026-10/20261010-unit"
STALE = {"code": "RECEIPT_STALE", "detail": "stale"}
HEAD, BASE = "a" * 40, "b" * 40


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = (tmp_path / "repo").resolve()
    (root / ".devkit").mkdir(parents=True)
    (root / ".devkit/config.toml").write_text("agents = []\n")
    (root / ".devkit/installation.json").write_text("{}")
    (root / SPEC).mkdir(parents=True)
    (root / SPEC / "spec.md").write_text("# Unit\n")

    async def base_policy(root, base, head, policy):
        return policy

    monkeypatch.setattr(services, "base_policy", base_policy)
    monkeypatch.setattr(services, "configured_version", lambda: "devkit-lock:unit")

    async def ensure_runtime():
        return root

    monkeypatch.setattr(services, "ensure_runtime", ensure_runtime)
    return root


def evaluation(monkeypatch, *, stale, lint_error=None, show_error=None, hold=None):
    """A devkit CLI double: the integration stage exits on lint-ci-clean and merge follows it."""

    async def restore(root):
        return [dict(STALE)] if stale else []

    async def cli(root, *args):
        if args[:2] == ("spec", "policy"):
            return {"approvals": {"dev-integration": {"policy": "ask"}}}
        if args[:2] == ("workflow", "show"):
            if show_error:
                raise show_error
            return {"id": "WF-unit", "hash": "hash", "stages": []}
        if args[:2] == ("workflow", "checks"):
            return {"checks": []}
        if args[:2] == ("workflow", "next"):
            linted = "lint-ci-clean" in args
            stage = {"id": "merge" if linted else "integrate", "exit": ["merged" if linted else "lint-ci-clean"]}
            return {"bound": True, "stage": stage, **(hold or {})}
        if args[:3] == ("workflow", "envelope", "check"):
            return {"envelopes": []}
        raise AssertionError(args)

    async def command(*args, cwd, **kwargs):
        if args[:2] == ("git-safe", "merge-base"):
            return BASE + "\n"
        if args[:3] == ("devkit", "rules", "check"):
            if lint_error:
                raise SddCommandError(lint_error, f"SDD evaluation failed ({lint_error}).")
            return "{}"
        raise AssertionError(args)

    monkeypatch.setattr(services, "restore", restore)
    monkeypatch.setattr(services, "cli", cli)
    monkeypatch.setattr(services, "command", command)


async def evaluate(root, approved=True):
    return await services.SddService().evaluate(root, SPEC, HEAD, BASE, None, approved)


async def test_stale_receipt_lint_load_failure_pauses_with_the_diagnostic(repo, monkeypatch):
    evaluation(monkeypatch, stale=True, lint_error="RULES_LOAD_FAILED")
    result = await evaluate(repo)
    assert result["integrated"] is False and result["lint_blocked"] is True
    assert result["lint_diagnostic"] == services.STALE_LINT
    assert result["current"]["stage"]["id"] == "integrate"
    assert result["warnings"] == [STALE]


@pytest.mark.parametrize(
    ("stale", "code"), [(False, "RULES_LOAD_FAILED"), (True, "RULES_RUN_FAILED"), (True, "COMMAND_FAILED")]
)
async def test_other_lint_failures_still_raise(repo, monkeypatch, stale, code):
    evaluation(monkeypatch, stale=stale, lint_error=code)
    with pytest.raises(SddCommandError) as result:
        await evaluate(repo)
    assert result.value.cli_code == code
    assert ("RECEIPT_STALE" in result.value.detail) is stale  # the hint rides along, the failure still blocks


async def test_violations_stay_repair_work_and_a_clean_lint_integrates_while_stale(repo, monkeypatch):
    evaluation(monkeypatch, stale=True, lint_error="RULES_VIOLATIONS")
    result = await evaluate(repo)
    assert not result["integrated"] and not result["lint_blocked"]
    assert "RULES_VIOLATIONS" in result["lint_diagnostic"]
    evaluation(monkeypatch, stale=True)
    result = await evaluate(repo)
    assert result["integrated"] and not result["lint_blocked"]
    assert result["current"]["stage"]["id"] == "merge"


async def test_later_refusal_names_the_stale_receipt_only_when_stale(repo, monkeypatch):
    drift = "SDD evaluation failed (WORKFLOW_DRIFT). Review the workflow change and explicitly rebind the spec."
    evaluation(monkeypatch, stale=True, show_error=SddCommandError("WORKFLOW_DRIFT", drift))
    with pytest.raises(SddCommandError) as result:
        await evaluate(repo, approved=False)
    assert result.value.detail.startswith(drift) and "RECEIPT_STALE" in result.value.detail
    assert result.value.cli_code == "WORKFLOW_DRIFT" and result.value.status == 422
    evaluation(monkeypatch, stale=False, show_error=SddCommandError("WORKFLOW_DRIFT", drift))
    with pytest.raises(ProjectError) as result:
        await evaluate(repo, approved=False)
    assert result.value.detail == drift


async def test_configuration_digest_uses_the_committed_receipt(repo, monkeypatch):
    committed = {"config": (repo / ".devkit/config.toml").read_text(), "receipt": "{}"}

    async def restore(root):
        (root / ".devkit/installation.json").write_text('{"regenerated": true}')
        return [dict(STALE)]

    evaluation(monkeypatch, stale=True)
    monkeypatch.setattr(services, "restore", restore)
    result = await evaluate(repo, approved=False)
    from app.features.project_management.pipeline_runs.requests import request_digest

    assert result["snapshot"]["configuration_digest"] == request_digest(committed)
    assert Path(repo / ".devkit/installation.json").read_text() != "{}"


async def test_unresolved_problem_holds_integration_and_is_reported(repo, monkeypatch):
    problem = {"file": "worker-02.yaml", "cause": "Build broke", "recovery": "Repair the fixture", "attempts": ["x"]}
    evaluation(monkeypatch, stale=False, hold={"blocked": True, "problems": [problem], "pending_questions": []})
    result = await evaluate(repo)
    assert result["hold"]["blocked"] and result["hold"]["problems"] == [problem]
    assert result["integrated"] is False and result["lint_diagnostic"] is None
    assert result["current"]["stage"]["id"] == "integrate"  # devkit itself passes no gate while held


async def test_pending_question_holds_integration_without_blocking(repo, monkeypatch):
    pending = [{"file": "worker-01.yaml", "id": "q1", "title": "Storage format"}]
    evaluation(monkeypatch, stale=False, hold={"blocked": False, "pending_questions": pending})
    result = await evaluate(repo)
    assert result["hold"] == {
        "blocked": False,
        "problems": [],
        "pending_questions": pending,
        "malformed_workers": [],
    }
    assert result["integrated"] is False


def test_read_hold_bounds_repository_text():
    current = {
        "blocked": True,
        "problems": [{"file": "w.yaml", "cause": "x" * 5000, "recovery": None, "attempts": list(range(20))}] * 30,
        "pending_questions": [{"file": "w.yaml", "id": "q1", "title": "t"}],
        "malformed_workers": [{"file": "bad.yaml", "reason": "no kind"}, "not-a-row"],
    }
    hold = services.read_hold(current)
    assert len(hold["problems"]) == 10 and len(hold["problems"][0]["cause"]) == 1000
    assert hold["problems"][0]["attempts"] == ["0", "1", "2", "3", "4"] and hold["problems"][0]["recovery"] == ""
    assert hold["malformed_workers"] == [{"file": "bad.yaml", "reason": "no kind"}]


async def test_runtime_status_probes_the_host_without_installing(monkeypatch):
    monkeypatch.setattr(services, "isolation_runner", lambda: "sandbox-exec")
    seen = []

    def isolated_python(writable, python, prefix, code, *args):
        seen.append(code)
        return ["/bin/echo", "3.13.2"]

    monkeypatch.setattr(services, "isolated_python", isolated_python)
    monkeypatch.setattr(services.SddService, "lock_status", lambda *args: pytest.fail("no project head given"))
    status = await services.SddService().runtime_status()
    assert status == {
        "profile": "repository-lock",
        "provider": "devkit-spec",
        "isolation": "sandbox-exec",
        "ok": True,
        "detail": "Python 3.13.2",
    }
    assert seen and "devkit" not in seen[0]

    def failing(*args):
        raise ProjectError(422, "requires an isolated runner", code="SDD_ISOLATION_UNAVAILABLE")

    monkeypatch.setattr(services, "isolated_python", failing)
    status = await services.SddService().runtime_status()
    assert status["ok"] is False and "isolated runner" in status["detail"]


@pytest.mark.parametrize(
    "state,expected",
    [("ready", "ready"), ("preparing", "preparing"), ("SDD_RUNTIME_SOURCE_UNAVAILABLE", "failed")],
)
async def test_project_lock_state_is_reported_with_its_identity(monkeypatch, tmp_path, state, expected):
    from contextlib import asynccontextmanager

    from app.features.project_management.sdd import runtime_cache
    from app.features.project_management.sdd.lock_runtime import Selection

    monkeypatch.setenv("AUTOHUB_SDD_CACHE", str(tmp_path / "cache"))
    identity = "c" * 64
    if state == "ready":
        runtime_cache.entry(identity).mkdir(parents=True)
        (runtime_cache.entry(identity) / "pin.json").write_text(
            '{"bundles": ["spec"], "revisions": {"devkit-spec": "' + "a" * 40 + '"}}'
        )

    @asynccontextmanager
    async def checkout(repository, head, base, token):
        yield tmp_path

    async def resolve(source, start=True):
        return Selection("dev", "x", identity, "3.13", (), ()), state

    monkeypatch.setattr(services, "checkout", checkout)
    monkeypatch.setattr(services, "current_source", lambda: None)
    monkeypatch.setattr(services, "resolve", resolve)
    status = await services.SddService().lock_status("o/r", HEAD, "token")
    assert status["state"] == expected and status["identity"] == identity
    if state == "ready":
        assert status["bundles"] == ["spec"] and status["revisions"] == {"devkit-spec": "a" * 40}
    if expected == "failed":
        assert "token" not in status["lock_detail"]


async def test_policy_notices_are_projected_but_do_not_change_execution_authority(repo, monkeypatch):
    evaluation(monkeypatch, stale=False)
    initial = services.cli
    payload = [{"code": "SPEC_APPROVAL_KEY_IGNORED", "level": "WARNING", "message": "secret-token"}]

    async def cli(root, *args):
        result = await initial(root, *args)
        return {**result, "notices": payload}

    monkeypatch.setattr(services, "cli", cli)
    result = await evaluate(repo, approved=False)
    assert [row["code"] for row in result["diagnostics"]] == ["SPEC_APPROVAL_KEY_IGNORED"]
    assert "notices" not in result["snapshot"]["policy"]
    assert "notices" not in result["workflow"] and "notices" not in result["current"]
    snapshot = {**result["snapshot"], "policy": {**result["snapshot"]["policy"], "notices": payload}}
    payload.clear()  # a legacy snapshot's nonsemantic notices do not become a drift check
    again = await services.SddService().evaluate(repo, SPEC, HEAD, BASE, snapshot, False)
    assert again["snapshot"] == result["snapshot"]
    changed = {**snapshot, "policy": {"approvals": {"dev-integration": {"policy": "auto"}}}}
    with pytest.raises(ProjectError, match="workflow or policy"):
        await services.SddService().evaluate(repo, SPEC, HEAD, BASE, changed, False)


async def test_prior_warnings_are_retained_when_a_later_cli_call_fails(repo, monkeypatch):
    evaluation(monkeypatch, stale=True, show_error=SddCommandError("WORKFLOW_DRIFT", "refused"))
    with pytest.raises(SddCommandError) as result:
        await evaluate(repo, approved=False)
    assert {row["code"] for row in result.value.diagnostics} == {"RECEIPT_STALE", "WORKFLOW_DRIFT"}


async def test_runtime_endpoint_reports_both_failures_without_an_error(monkeypatch):
    """A host without isolation and an unreadable head still yield a status (not a server error)."""
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from app.features.project_management.sdd import usecases

    @asynccontextmanager
    async def transaction():
        yield None

    class Projects:
        async def get(self, session, project_id):
            return SimpleNamespace(github_repository="o/r", github_connector_id="connector")

    class Observer:
        async def get_token(self, connector, kind):
            raise ProjectError(422, "connector unavailable")

    async def runtime_status(self, *args):
        return {"profile": "repository-lock", "isolation": None, "ok": False, "state": None, "detail": "no sandbox"}

    monkeypatch.setattr(usecases, "AsyncTransaction", transaction)
    monkeypatch.setattr(services.SddService, "runtime_status", runtime_status)
    use_case = usecases.SddUseCase.__new__(usecases.SddUseCase)
    use_case.projects, use_case.observer = Projects(), Observer()  # type: ignore[assignment]
    status = await use_case.runtime("project")
    assert status.ok is False and status.state == "failed" and status.lock_detail


async def test_lock_status_reports_preparing_while_an_eviction_holds_the_entry(monkeypatch, tmp_path):
    from contextlib import asynccontextmanager, contextmanager

    from app.features.project_management.sdd import runtime_cache
    from app.features.project_management.sdd.lock_runtime import Selection

    @asynccontextmanager
    async def checkout(repository, head, base, token):
        yield tmp_path

    async def resolve(source, start=True):
        return Selection("dev", "x", "c" * 64, "3.13", (), ()), "ready"

    @contextmanager
    def busy(identity):
        raise BlockingIOError
        yield  # pragma: no cover

    monkeypatch.setattr(services, "checkout", checkout)
    monkeypatch.setattr(services, "current_source", lambda: None)
    monkeypatch.setattr(services, "resolve", resolve)
    monkeypatch.setattr(runtime_cache, "lease", busy)
    status = await services.SddService().lock_status("o/r", HEAD, "token")
    assert status["state"] == "preparing"


async def test_host_probe_timeout_kills_the_sandboxed_process_group(monkeypatch, tmp_path):
    import asyncio
    import os

    marker = tmp_path / "child.pid"
    script = f"sleep 30 & echo $! > {marker}; wait"
    real_timeout = asyncio.timeout
    monkeypatch.setattr(services.asyncio, "timeout", lambda seconds: real_timeout(0.5))
    with pytest.raises(TimeoutError):
        await services._probe(["/bin/sh", "-c", script], tmp_path)
    child = int(marker.read_text())
    await asyncio.sleep(0.2)
    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)
