"""The units Hub evaluates: a spec bundle or a proposal bundle, told apart by directory and anchor."""

import re
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError

UNIT_PATTERN = r"^(specs/[0-9]{4}-[0-9]{2}/[a-zA-Z0-9_-]+|docs/proposals/PROP-[a-z0-9][a-z0-9_-]*)$"
_SPEC = re.compile(r"^specs/[0-9]{4}-[0-9]{2}/[a-zA-Z0-9_-]+$")
_PROPOSAL = re.compile(r"^docs/proposals/PROP-([a-z0-9][a-z0-9_-]*)$")
# A frontmatter ``status:`` line, plain or quoted, keeping a trailing comment (the shape devkit-spec scaffolds).
_STATUS = re.compile(r"""^status:[ \t]*['"]?([a-z]+)['"]?(?=[ \t]*\r?$|[ \t]+#)""", re.MULTILINE)


def is_proposal(unit: str) -> bool:
    return _PROPOSAL.fullmatch(unit) is not None


def proposal_slug(unit: str) -> str:
    match = _PROPOSAL.fullmatch(unit)
    if match is None:
        raise ProjectError(422, "Proposal decisions apply to proposal units (docs/proposals/PROP-<slug>)")
    return match.group(1)


def unit_anchor(unit: str) -> str | None:
    """The anchor file of a unit directory, or ``None`` when the path names neither kind of unit."""
    if is_proposal(unit):
        return "proposal.md"
    if _SPEC.fullmatch(unit):
        return "spec.md"
    return None


def _frontmatter_span(text: str) -> tuple[int, int] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    return (0, end + 4) if end >= 0 else None


def read_status(root: Path, unit: str) -> str | None:
    """The frontmatter ``status`` of the unit's anchor; ``None`` without a readable one."""
    anchor = unit_anchor(unit)
    if anchor is None:
        return None
    try:
        text = (root / unit / anchor).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    span = _frontmatter_span(text)
    if span is None:
        return None
    match = _STATUS.search(text, span[0], span[1])
    return match.group(1) if match else None


def set_status(root: Path, unit: str, current: str, new: str) -> None:
    """Rewrite the anchor's ``status:`` line from ``current`` to ``new``; nothing else in the file changes.

    The same line rewrite devkit-spec's handoff applies; the file is never re-serialized.
    """
    anchor = unit_anchor(unit)
    path = root / unit / (anchor or "")
    if anchor is None or not path.is_file():
        raise ProjectError(422, "The unit has no anchor to record the decision in")
    text = path.read_text(encoding="utf-8")
    span = _frontmatter_span(text)
    match = _STATUS.search(text, span[0], span[1]) if span else None
    if match is None or match.group(1) != current:
        found = match.group(1) if match else "without a status"
        raise ProjectError(409, f"Proposal is {found}, not {current}; inspect the latest result and decide again")
    path.write_text(text[: match.start()] + f"status: {new}" + text[match.end() :], encoding="utf-8")
