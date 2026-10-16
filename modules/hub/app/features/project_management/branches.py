"""Activity branch names, shared with the local Host (strategy layer 01 section 4.7).

One slug has one branch per activity: ``plan-<slug>`` for Planning, ``dev-<slug>`` for Development. A branch that
already exists on the remote means that activity is in progress somewhere, so a new start is refused and the work
is reused only through an explicit attach. Hub applies the rule to the remote branches it can see; branches that
were never pushed are the local Host's to check before it registers cloud work.
"""

import re

ACTIVITY_BRANCH = re.compile(r"^(plan|dev)-[a-z0-9][a-z0-9_-]*$")
MAX_BRANCH_LENGTH = 64
ACTIVITY_BRANCH_RULE = "plan-<slug> or dev-<slug> with a slug of [a-z0-9][a-z0-9_-]*, at most 64 characters in all"
_SPEC_UNIT = re.compile(r"^specs/\d{4}-\d{2}/\d{8}-([a-z0-9][a-z0-9_-]*)$")
_PROPOSAL_UNIT = re.compile(r"^docs/proposals/PROP-([a-z0-9][a-z0-9_-]*)/?$")


def is_activity_branch(name: str) -> bool:
    return len(name) <= MAX_BRANCH_LENGTH and ACTIVITY_BRANCH.fullmatch(name) is not None


def item_branch(key: str) -> str:
    """A Work Plan Item is Development on the cloud ``session`` path: ``dev-<slug>``, the slug being its key."""
    name = f"dev-{key.lower()}"
    if not is_activity_branch(name):
        raise ValueError(f"Item key {key!r} does not make an activity branch ({ACTIVITY_BRANCH_RULE})")
    return name


def unit_branch(unit_dir: str, activity: str | None = None) -> str | None:
    """The activity branch a unit is worked on: ``dev-<slug>`` for a spec, ``plan-<slug>`` for a proposal.

    ``activity`` ``"dev"`` names the Development branch of an accepted proposal, where the handoff that turns it into
    a spec is the first step. ``None`` when the path names no unit with a slug the branch grammar accepts.
    """
    if spec := _SPEC_UNIT.fullmatch(unit_dir):
        return f"dev-{spec.group(1)}"
    if proposal := _PROPOSAL_UNIT.fullmatch(unit_dir):
        return f"{activity or 'plan'}-{proposal.group(1)}"
    return None


def activity_branch(activity: str, slug: str) -> str:
    name = f"{activity}-{slug}"
    if activity not in ("plan", "dev") or not is_activity_branch(name):
        raise ValueError(f"{name!r} is not an activity branch ({ACTIVITY_BRANCH_RULE})")
    return name


def unit_branch_mismatch(unit_dir: str, head_ref: str, activity: str | None = None) -> str | None:
    """Why a pull request cannot be attached to ``unit_dir``, or ``None`` when its head is the unit's branch."""
    expected = unit_branch(unit_dir, activity)
    if expected is None:
        return f"{unit_dir} does not name a unit slug the activity branch rule accepts ({ACTIVITY_BRANCH_RULE})"
    if head_ref != expected:
        return (
            f"{unit_dir} is worked on branch {expected}; this pull request's head is {head_ref}. "
            "Open the pull request from that branch, or enroll the pull request that has it"
        )
    return None
