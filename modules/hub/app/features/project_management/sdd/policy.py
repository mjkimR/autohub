"""Read owning-base policy through devkit, never through a second configuration parser."""

from pathlib import Path

from .checkout import checkout, command
from .runtime import restore

SIZES = ("S", "M", "L")
ADAPTIVE_DEV = "adaptive-dev"
LIFECYCLE_INACTIVE = (
    "The repository's [development] approach is adaptive-dev, so devkit-spec refuses proposal acceptance and handoff "
    '(SPEC_LIFECYCLE_INACTIVE); choose approach = "sdd" in .devkit/config.toml to use the SDD lifecycle'
)


def development_approach(policy: dict | None) -> str:
    """Read current policy and saved pre-0.1.6 snapshots; absent approaches default to ``sdd``."""
    development = (policy or {}).get("development")
    approach = development.get("approach") if isinstance(development, dict) else None
    if approach == "incubation":  # historical run evidence, not a supported repository configuration
        return ADAPTIVE_DEV
    return approach if isinstance(approach, str) and approach else "sdd"


def size_blocker(size: str | None) -> str | None:
    """devkit-spec's decomposition gate: ``size`` absent, empty, ``S``, ``M`` or ``L`` passes; anything else (XL)."""
    return None if not size or size in SIZES else f"size {size}"


async def base_policy(root: Path, base: str, head: str, head_policy: dict) -> dict:
    if base == head:
        return head_policy
    from .services import cli, committed_configuration

    directory = root / ".devkit/transient" / f"hub-base-{base}"
    await command("git-safe", "worktree", "add", "--quiet", "--detach", str(directory), base, cwd=root)
    try:
        committed_configuration(directory)
        return await cli(root, "spec", "policy", "-w", str(directory))
    finally:
        await command("git-safe", "worktree", "remove", "--force", str(directory), cwd=root)


def planning_blocker(current: dict, slug: str) -> str | None:
    """Why ``workflow next`` on the base does not let the draft start Planning, or ``None`` when plan-intent is done."""
    if current.get("errors"):
        code = str((current["errors"][0] or {}).get("code") or "an invalid record")
        return f"PROP-{slug} has invalid workflow evidence on the base ({code}); repair it in Backlog before Planning"
    if "intent-proposal" in current.get("done", []):
        return None
    for check in current.get("unmet") or []:
        name = str(check.get("name", ""))
        if name.startswith("frontmatter(proposal.md size") and not check.get("satisfied"):
            detail = str(check.get("detail") or "size outside S, M or L")
            return f"PROP-{slug} fails the size gate ({detail}); decompose it in Backlog before Planning"
    return f"Record plan-intent for PROP-{slug} in Backlog before Planning"


async def start_blocker(repository: str, base: str, token: str, unit: str, activity: str) -> str | None:
    """Why the base refuses to start ``activity`` for ``unit``, read through devkit in one checkout; ``None`` if not."""
    async with checkout(repository, base, base, token) as root:
        await restore(root)
        return await admission_blocker(root, unit, activity)


async def admission_blocker(root: Path, unit: str, activity: str) -> str | None:
    """Existing native admission inside an already restored read-only evaluation checkout."""
    from .services import cli

    if development_approach(await cli(root, "spec", "policy")) == ADAPTIVE_DEV:
        return LIFECYCLE_INACTIVE
    if activity != "plan":
        return None
    current = await cli(root, "workflow", "next", "--unit", unit)
    return planning_blocker(current, unit.rsplit("PROP-", 1)[-1])
