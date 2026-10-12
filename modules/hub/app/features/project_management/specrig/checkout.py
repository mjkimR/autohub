"""Disposable read-only evaluation checkouts; no repository code is executed."""

import asyncio
import base64
import os
import re
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from app.features.project_management.projects.errors import ProjectError

CLI_FIXES = {
    "GIT_SNAPSHOT_FAILED": "Verify the exact Git head/base commits and fetch the required history.",
    "UNEXPECTED_ERROR": "The CLI could not evaluate the repository; inspect the pinned runtime and installation.",
    "HARNESS_RESTORE_REQUIRED": "Restore the recorded release before inspection.",
    "WORKFLOW_DRIFT": "Review the workflow change and explicitly rebind the spec.",
    "WORKFLOW_NOT_FOUND": "Restore the bound workflow or repair the spec binding.",
    "CUSTOM_RULES_REQUIRE_GO": "This runner supports bundled rules only; custom Go rules need a separate runner.",
    "RULES_BUILD_FAILED": "The rule runtime could not be prepared; inspect the runner configuration.",
    "RULES_RUNNER_ERROR": "The rule runtime failed; inspect the runner configuration.",
    "RULE_VIOLATIONS_DETECTED": "Fix the reported rules in the repository and rerun final lint.",
    "INSTALLATION_FAILED": "Provision the matching release in the server's offline cache.",
    "INSTALLATION_INPUT": "Check the installation receipt against the pinned release.",
    "INSTALLATION_CONFLICT": "Resolve modified managed files before restoring the release.",
}


class SpecrigCommandError(ProjectError):
    def __init__(self, cli_code: str, detail: str):
        self.cli_code = cli_code
        super().__init__(422, detail, code=f"SPECRIG_{cli_code}")


async def command(*args: str, cwd: Path, env: dict | None = None, allow_failure: bool = False) -> str:
    if args[0] == "specrig":
        # Never expose server secrets, Go, or a repository-provided runner cache to CLI checks.
        shutil.rmtree(cwd / ".specrig/.cache", ignore_errors=True)
        with TemporaryDirectory(prefix="autohub-cli-tools-") as directory:
            for name in ("git", "specrig"):
                binary = shutil.which(name)
                if binary is None:
                    raise ProjectError(422, f"Specrig runner is missing {name}; provision the pinned runtime")
                (Path(directory) / name).symlink_to(Path(binary).resolve())
            return await _command(
                *args,
                cwd=cwd,
                env={"PATH": directory, "TMPDIR": str(Path(directory).resolve()), "LANG": "C.UTF-8"},
                allow_failure=allow_failure,
            )
    return await _command(*args, cwd=cwd, env=env, allow_failure=allow_failure)


async def _command(*args: str, cwd: Path, env: dict | None, allow_failure: bool) -> str:
    process = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        async with asyncio.timeout(25):
            stdout, stderr = await process.communicate()
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise
    if process.returncode and not allow_failure:
        if args[0] == "specrig":
            diagnostic = stderr.decode(errors="replace")
            found = re.search(r"\[ERROR\]\s+\(([A-Z_]+)\)", diagnostic)
            code = found.group(1) if found and found.group(1) in CLI_FIXES else "COMMAND_FAILED"
            fix = CLI_FIXES.get(code, "Inspect the CLI installation and repository contract.")
            rules = sorted(set(re.findall(r"\[([A-Z]+-[A-Za-z0-9_-]+)\]", stdout.decode(errors="replace"))))[:10]
            detail = f"Specrig {args[1]} failed ({code}). {fix}"
            if code == "RULE_VIOLATIONS_DETECTED" and rules:
                detail += " Rules: " + ", ".join(rules)
            raise SpecrigCommandError(code, detail)
        raise ProjectError(
            422,
            "Git checkout failed; check repository access and the requested commits",
            code="SPECRIG_CHECKOUT_FAILED",
        )
    return stdout.decode() if not process.returncode else ""


@asynccontextmanager
async def checkout(repository: str, head: str, base: str, token: str):
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (head, base)):
        raise ProjectError(422, "Specrig requires exact Git head and base commits")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ProjectError(422, "Invalid repository")
    with TemporaryDirectory(prefix="autohub-specrig-") as directory:
        root = Path(directory).resolve()
        await command("git", "init", "--quiet", cwd=root)
        # Pass credentials only to fetch, never in arguments, files, snapshots or errors.
        credential = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {credential}",
            "GIT_CONFIG_KEY_1": "credential.helper",
            "GIT_CONFIG_VALUE_1": "",
        }
        await command(
            "git",
            "fetch",
            "--quiet",
            "--no-tags",
            "--no-recurse-submodules",
            f"https://github.com/{repository}.git",
            head,
            base,
            cwd=root,
            env=env,
        )
        await command("git", "-c", "core.hooksPath=/dev/null", "checkout", "--quiet", "--detach", head, cwd=root)
        # Harness/spec symlinks must not escape the disposable checkout into host files.
        for directory_name in (".specrig", "specs", "docs"):
            directory_path = root / directory_name
            for path in [directory_path, *directory_path.rglob("*")]:
                if path.is_symlink():
                    raise ProjectError(422, "Specrig evaluation does not accept symlinked harness or evidence files")
        yield root
