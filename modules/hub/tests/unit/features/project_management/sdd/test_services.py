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
    monkeypatch.setattr(services, "configured_version", lambda: "devkit-spec:unit")
    monkeypatch.setattr(services, "revision_warnings", lambda root: [])
    return root


def evaluation(monkeypatch, *, stale, lint_error=None, show_error=None):
    """A devkit CLI double: the integration stage exits on lint-ci-clean and merge follows it."""

    async def restore(root):
        return [dict(STALE)] if stale else []

    async def cli(root, *args):
        if args[:2] == ("spec", "policy"):
            return {"approvals": {"integration": {"policy": "ask"}}}
        if args[:2] == ("workflow", "show"):
            if show_error:
                raise show_error
            return {"id": "WF-unit", "hash": "hash", "stages": []}
        if args[:2] == ("workflow", "checks"):
            return {"checks": []}
        if args[:2] == ("workflow", "next"):
            linted = "lint-ci-clean" in args
            return {
                "bound": True,
                "stage": {"id": "merge" if linted else "integrate", "exit": ["merged" if linted else "lint-ci-clean"]},
            }
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
