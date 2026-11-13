"""Recognized unit path syntax and display-only metadata parsing."""

import re

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
