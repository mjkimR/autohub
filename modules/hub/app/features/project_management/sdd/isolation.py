"""OS isolation for Python rules and workflow checks; there is no unsandboxed fallback."""

import json
import shutil
import sys
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError


def isolation_runner() -> str | None:
    """The sandbox this host would use, or None when it has none (then every evaluation is refused)."""
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        return "sandbox-exec"
    if sys.platform == "linux" and shutil.which("bwrap"):
        return "bubblewrap"
    return None


def isolated_command(
    home: Path, root: Path, args: tuple[str, ...], python_prefix: str, *, git: bool = False
) -> list[str]:
    python = str(home / ".venv/bin/python")
    invocation = (
        ["/usr/bin/git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", *args]
        if git
        else [python, "-I", "-B", "-m", "devkit_dist", *args]
    )
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        readable = [
            home,
            Path(python_prefix),
            Path("/usr"),
            Path("/bin"),
            Path("/System"),
            Path("/Library/Apple"),
            Path("/Library/Developer"),
            Path("/private/var/db/dyld"),
            Path("/private/etc"),
            Path("/dev"),
        ]
        profile = "(version 1)(deny default)(allow process*)(allow sysctl-read)(allow file-read-metadata)"
        profile += (
            '(allow file-read* (literal "/"))(allow mach-lookup)(allow file-read* file-write* (literal "/dev/null"))'
        )
        profile += "".join(f"(allow file-read* (subpath {json.dumps(str(p))}))" for p in readable)
        profile += f"(allow file-read* file-write* (subpath {json.dumps(str(root))}))"
        return ["/usr/bin/sandbox-exec", "-p", profile, *invocation]
    if sys.platform == "linux" and (bwrap := shutil.which("bwrap")):
        cmd = [bwrap, "--die-with-parent", "--new-session", "--unshare-all", "--cap-drop", "ALL"]
        for path in dict.fromkeys(["/usr", "/bin", "/lib", "/lib64", python_prefix, str(home)]):
            if Path(path).exists():
                cmd.extend(["--ro-bind", path, path])
        cmd.extend(["--proc", "/proc", "--dev", "/dev", "--bind", str(root), str(root), "--chdir", str(root)])
        return [*cmd, *invocation]
    raise ProjectError(
        422,
        "SDD evaluation requires an isolated runner (bubblewrap on Linux, sandbox-exec on macOS)",
        code="SDD_ISOLATION_UNAVAILABLE",
    )
