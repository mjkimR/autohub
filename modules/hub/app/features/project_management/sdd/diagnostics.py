"""Bounded, Hub-owned projections of untrusted devkit diagnostics.

Only recognized codes select display text. Repository messages, advisory fixes, paths and stderr never become
operator diagnostics. The task-local collector follows one evaluation, including its sync and base-policy reads.
"""

from contextlib import contextmanager
from contextvars import ContextVar

from app.features.project_management.projects.errors import ProjectError

CLI_FIXES = {
    "RULES_VIOLATIONS": "Fix the reported rule violations and run the final checks again.",
    "RULES_SNAPSHOT_FAILED": "Verify the Git history and isolated Git runtime.",
    "RULES_RUN_FAILED": "Inspect the rule runtime; evaluation could not finish.",
    "RECEIPT_STALE": "Update and commit the receipt with the supported runtime before enrolling.",
    "SYNC_CONFLICT": "Resolve the file conflict devkit sync reported in the repository and commit the result.",
    "OVERRIDE_DRIFT": "Review the override drift devkit sync reported and commit the resolved overrides.",
    "RULES_LOAD_FAILED": "Commit the receipt produced by the reviewed runtime; the recorded rules did not load.",
    "SELECTION_INVALID": "Provision the project's selected bundles in the reviewed runtime profile.",
    "WORKFLOW_DRIFT": "Review the workflow change and explicitly rebind the spec.",
    "DECISION_RECORD_INVALID": "Repair the invalid decision record before resuming.",
    "ENVELOPE_INVALID": "Repair the invalid report before resuming.",
    "SPEC_PROPOSAL_ACCEPT_REFUSED": "Inspect the proposal status and binding before requesting acceptance again.",
    "SPEC_PROPOSAL_NOT_ELIGIBLE": "Complete the proposal's required Planning checks before accepting it.",
    "SPEC_PROPOSAL_GATE_NOT_OPEN": "Complete Planning and answer pending questions before accepting the proposal.",
    "SPEC_PROPOSAL_WRONG_WORKTREE": "Accept the proposal on its own plan-<slug> branch.",
    "SPEC_PROPOSAL_POLICY_NOT_AUTO": (
        "The owning base's plan-accept policy is not auto: accept the proposal as the user, or set "
        'plan-accept = "auto" in [workflow.approvals] of the base\'s .devkit/config.toml.'
    ),
    "SPEC_LIFECYCLE_INACTIVE": (
        "The repository's [development] approach is adaptive-dev, which disables proposal acceptance and handoff; "
        'set approach = "sdd" in .devkit/config.toml to use the SDD lifecycle.'
    ),
    "DEVELOPMENT_CONFIG_INVALID": (
        'Set [development] to only approach = "sdd" or "adaptive-dev" in .devkit/config.toml and commit it.'
    ),
    "SPEC_CONFIG_INVALID": (
        "Correct the devkit-spec configuration in .devkit/config.toml ([tool.spec], or [workflow.approvals] and "
        "[worktree] for an acceptance) and commit it."
    ),
    "COMMAND_FAILED": "Inspect the isolated runtime and repository contract.",
}

CLI_FIXES.update(
    {
        "SDD_RUNTIME_UNAVAILABLE": "Provision the reviewed SDD runtime with just install-sdd and verify its lock.",
        "SDD_PROFILE_INVALID": "Correct the server-owned SDD runtime profiles and repository mappings.",
        "SDD_BUNDLES_MISSING": "Provision a reviewed runtime profile containing the repository's selected bundles.",
        "SDD_RECEIPT_MISSING": "Commit the repository's devkit configuration and installation receipt before enrolling.",
    }
)
LIMIT = 20
_collected: ContextVar[list[dict] | None] = ContextVar("sdd_diagnostics", default=None)
_RUNTIME = {
    "RULES_SNAPSHOT_FAILED",
    "RULES_RUN_FAILED",
    "RULES_LOAD_FAILED",
    "SELECTION_INVALID",
    "COMMAND_FAILED",
    "SDD_RUNTIME_UNAVAILABLE",
    "SDD_PROFILE_INVALID",
    "SDD_BUNDLES_MISSING",
    "RUNTIME_REVISION_MISMATCH",
}
_DECISION = {"SPEC_PROPOSAL_GATE_NOT_OPEN", "SPEC_PROPOSAL_POLICY_NOT_AUTO"}
_TARGETS = {
    "RECEIPT_STALE": [".devkit/installation.json"],
    "SDD_RECEIPT_MISSING": [".devkit/config.toml", ".devkit/installation.json"],
    "SPEC_CONFIG_INVALID": [".devkit/config.toml"],
    "DEVELOPMENT_CONFIG_INVALID": [".devkit/config.toml"],
    "SPEC_LIFECYCLE_INACTIVE": [".devkit/config.toml"],
    "SPEC_APPROVAL_KEY_IGNORED": [".devkit/config.toml"],
    "RUNTIME_REVISION_MISMATCH": ["uv.lock"],
}
_NOTICES = {
    "SPEC_APPROVAL_KEY_IGNORED": (
        "An approval setting has no effect in this devkit runtime.",
        "Review and remove retired or non-gate approval keys from .devkit/config.toml before the next enrollment.",
    ),
    "RECEIPT_STALE": (
        "The committed devkit receipt differs from the reviewed runtime.",
        "Align and commit the receipt with the reviewed runtime, then enroll a new execution.",
    ),
    "RUNTIME_REVISION_MISMATCH": (
        "The repository and reviewed runtime use different devkit revisions.",
        "Review the repository lock and runtime revision before continuing.",
    ),
    "POST_SYNC_NOTICE": (
        "Devkit reported an informational synchronization notice.",
        "Continue with the inspected workflow; no retry is needed.",
    ),
    "DEVKIT_NOTICE": (
        "Devkit reported an additional notice whose details are not exposed by Hub.",
        "Inspect devkit output in a trusted repository checkout if more context is needed.",
    ),
}


def diagnostic(code: str, *, severity: str = "error") -> dict:
    """Select only catalog-owned values; even the displayed code cannot be repository-authored."""
    known = (
        code
        if isinstance(code, str) and (code in CLI_FIXES or code in _NOTICES)
        else ("COMMAND_FAILED" if severity == "error" else "DEVKIT_NOTICE")
    )
    if severity != "error" and known in _NOTICES:
        message, action = _NOTICES[known]
    else:
        message = f"Devkit {'evaluation failed' if severity == 'error' else 'reported a notice'} ({known})."
        action = CLI_FIXES.get(known, CLI_FIXES["COMMAND_FAILED"])
    return {
        "code": known,
        "severity": severity if severity in ("error", "warning", "info") else "warning",
        "category": "runtime" if known in _RUNTIME else "decision" if known in _DECISION else "repository",
        "message": message,
        "action": action,
        "retry": "after_fix" if severity == "error" else "never",
        "target_files": list(_TARGETS.get(known, [])),
    }


def merge(*groups: list[dict]) -> list[dict]:
    """Keep actionable errors even when earlier reads filled the notice budget."""
    rows: list[dict] = []
    for severity in ("error", "warning", "info"):
        for group in groups:
            for row in group[:LIMIT]:
                if row.get("severity") == severity and row not in rows and len(rows) < LIMIT:
                    rows.append(row)
    return rows


def notices(payload) -> list[dict]:
    """The JSON notice list is input data, never a source of operator text or executable actions."""
    if not isinstance(payload, dict) or not isinstance(payload.get("notices"), list):
        return []
    rows = []
    for notice in payload["notices"][:LIMIT]:
        if not isinstance(notice, dict):
            continue
        code = notice.get("code")
        if not isinstance(code, str):
            code = "DEVKIT_NOTICE"
        rows.append(diagnostic(code, severity="info" if notice.get("level") == "NOTICE" else "warning"))
    return merge(rows)


def remember(diagnostics: list[dict]) -> None:
    if (rows := _collected.get()) is not None:
        rows[:] = merge(rows, diagnostics)


def collect(payload) -> None:
    remember(notices(payload))


@contextmanager
def capture():
    """Nested reads share their evaluation collector; concurrent evaluations never do."""
    existing = _collected.get()
    if existing is not None:
        yield existing
        return
    rows: list[dict] = []
    token = _collected.set(rows)
    try:
        yield rows
    finally:
        _collected.reset(token)


def failure(exc) -> list[dict]:
    rows = getattr(exc, "diagnostics", None)
    if isinstance(rows, list):
        return rows
    return [diagnostic(getattr(exc, "code", "COMMAND_FAILED"))]


class SddEvaluationError(ProjectError):
    """Retain an evaluation failure's HTTP contract alongside its safe operator diagnostics."""

    def __init__(self, error: ProjectError, diagnostics: list[dict]):
        super().__init__(
            error.status,
            error.detail,
            code=error.code,
            actor=error.advisory.actor,
            retry=error.advisory.retry,
            fix=error.advisory.fix,
        )
        self.diagnostics = diagnostics
