"""Read owning-base policy through devkit, never through a second configuration parser."""

from pathlib import Path

from .checkout import checkout, command
from .runtime import restore


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


async def planning_intent(repository: str, base: str, token: str, unit: str) -> bool:
    from .services import cli

    async with checkout(repository, base, base, token) as root:
        await restore(root)
        current = await cli(root, "workflow", "next", "--unit", unit)
        return "intent-proposal" in current.get("done", []) and not current.get("errors")
