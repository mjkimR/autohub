"""Reviewer evidence preserves run/round identity; presentation limits never drive mutations."""

from pathlib import Path

import yaml

KINDS = ("final-report", "review", "reverify", "worker", "challenger", "scout", "reconcile-check")


def anchor_metadata(root: Path, unit: str) -> dict:
    from .units import unit_anchor

    path = root / unit / (unit_anchor(unit) or "spec.md")
    if not path.is_file():
        return {}
    parts = path.read_text().split("---", 2)
    try:
        data = yaml.safe_load(parts[1]) if len(parts) == 3 else {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def proposal_metadata(root: Path, unit: str) -> dict:
    data = anchor_metadata(root, unit)
    return {
        key: value
        for key in ("planning_effort", "dev_effort", "milestone", "needs_decompose")
        if (value := data.get(key)) in ("low", "medium", "high")
        or (key == "milestone" and isinstance(value, str))
        or (key == "needs_decompose" and isinstance(value, bool))
    }


def reports(envelopes: dict) -> list[dict]:
    rows = []
    for kind in KINDS:
        for row in sorted(
            (r for r in envelopes.get("envelopes", []) if r.get("kind") == kind), key=lambda r: r.get("seq", 0)
        ):
            rows.append(
                {
                    "kind": kind,
                    "file": row["file"],
                    "status": row["status"],
                    "seq": row.get("seq"),
                    "stage": row.get("stage"),
                    "workflow": row.get("workflow"),
                    "segment": row.get("segment"),
                    "review": row.get("review"),
                    "activity_effort": row.get("activity_effort"),
                    "created_at": row.get("created_at"),
                    "diff_scope": row.get("diff_scope"),
                    "summary": str(row.get("summary", ""))[:4000],
                    "checks": {str(k): str(v)[:1000] for k, v in list((row.get("checks") or {}).items())[:20]},
                    "findings": row.get("findings", []),
                    "assumptions": row.get("assumptions", []),
                    "unverified_areas": row.get("unverified_areas", []),
                }
            )
    return rows


def in_context(row: dict, context: dict) -> bool:
    """Use devkit's legacy-envelope scoping: absent workflow/segment counts in any matching segment."""
    return not row.get("workflow") or (
        row["workflow"] == context.get("workflow")
        and (row.get("segment") is None or row["segment"] == context.get("segment"))
    )


def review_gaps(rows: list[dict], context: dict) -> list[str]:
    """Guidance only: devkit owns gates. A supporting round must belong to its worker's segment/workflow."""
    gaps = []
    for worker in (r for r in rows if r["kind"] == "worker" and in_context(r, context)):
        if worker.get("workflow") and worker["workflow"] != "sdd-proposal":
            continue
        effort = worker.get("activity_effort")
        matching = [r for r in rows if in_context(r, context)]
        for kind in ("challenger", "scout") if effort == "high" else ("challenger",) if effort == "medium" else ():
            if not any(r["kind"] == kind for r in matching):
                gaps.append(f"{worker['file']}: {effort} effort has no {kind} record in this workflow segment")
    return gaps
