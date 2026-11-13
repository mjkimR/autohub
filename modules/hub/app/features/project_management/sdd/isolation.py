"""OS isolation for repository code: rules, workflow checks and source builds; there is no unsandboxed fallback.

Every sandbox has exactly one writable directory, reads the system and the listed paths only, has no network and
inherits no credentials (the caller passes a minimal environment).
"""

import json
import shutil
import sys
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError

GIT = "/usr/bin/git"


def isolation_runner() -> str | None:
    """The sandbox this host would use, or None when it has none (then every evaluation is refused)."""
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        return "sandbox-exec"
    if sys.platform == "linux" and shutil.which("bwrap"):
        return "bubblewrap"
    return None


def sandboxed(writable: Path, readable: list[Path], invocation: list[str]) -> list[str]:
    """Wrap ``invocation`` so it can write only ``writable`` and read the system plus ``readable``."""
    readable = [Path(path) for path in dict.fromkeys(str(path) for path in readable if path)]
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        system = [
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
        profile += "".join(f"(allow file-read* (subpath {json.dumps(str(p))}))" for p in [*readable, *system])
        profile += f"(allow file-read* file-write* (subpath {json.dumps(str(writable))}))"
        return ["/usr/bin/sandbox-exec", "-p", profile, *invocation]
    if sys.platform == "linux" and (bwrap := shutil.which("bwrap")):
        cmd = [bwrap, "--die-with-parent", "--new-session", "--unshare-all", "--cap-drop", "ALL"]
        for path in dict.fromkeys(["/usr", "/bin", "/lib", "/lib64", *(str(p) for p in readable)]):
            if Path(path).exists():
                cmd.extend(["--ro-bind", path, path])
        cmd.extend(["--proc", "/proc", "--dev", "/dev", "--bind", str(writable), str(writable)])
        return [*cmd, "--chdir", str(writable), *invocation]
    raise ProjectError(
        422,
        "SDD evaluation requires an isolated runner (bubblewrap on Linux, sandbox-exec on macOS)",
        code="SDD_ISOLATION_UNAVAILABLE",
    )


def isolated_command(home: Path, root: Path, args: tuple[str, ...], python_prefix: str) -> list[str]:
    """devkit from a resolved runtime's venv, writing only the checkout."""
    python = str(home / ".venv/bin/python")
    return sandboxed(root, [home, Path(python_prefix)], [python, "-I", "-B", "-m", "devkit_dist", *args])


def isolated_git(root: Path, args: tuple[str, ...]) -> list[str]:
    """The image's Git on the checkout; it never needs a devkit runtime."""
    invocation = [GIT, "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", *args]
    return sandboxed(root, [], invocation)


def isolated_build(staging: Path, build_python: Path, uv: Path, args: tuple[str, ...]) -> list[str]:
    """uv building a locked source offline with the image's pinned backend; writes only the staging directory."""
    readable = [build_python.parent.parent, Path(sys.base_prefix), uv.parent]
    return sandboxed(staging, readable, [str(uv), *args])


def isolated_python(writable: Path, python: Path, prefix: str, code: str, *args: str) -> list[str]:
    """An interpreter started inside the sandbox: the host probe and a new runtime's inventory probe."""
    readable = [python.parent.parent, Path(prefix)]
    return sandboxed(writable, readable, [str(python), "-I", "-B", "-c", code, *args])
