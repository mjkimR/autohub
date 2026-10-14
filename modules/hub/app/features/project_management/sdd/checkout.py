"""Disposable evaluation checkouts; Python extensions execute only inside OS isolation."""

import asyncio
import base64
import json
import os
import re
import signal
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from tempfile import TemporaryDirectory

from app.features.project_management.projects.errors import ProjectError

CLI_FIXES = {
    "RULES_VIOLATIONS": "Fix the reported rule violations and run the final checks again.",
    "RULES_SNAPSHOT_FAILED": "Verify the Git history and isolated Git runtime.",
    "RULES_RUN_FAILED": "Inspect the rule runtime; evaluation could not finish.",
    "RECEIPT_STALE": "Update and commit the receipt with the supported runtime before enrolling.",
    "SELECTION_INVALID": "Provision the project's selected bundles in the reviewed runtime profile.",
    "WORKFLOW_DRIFT": "Review the workflow change and explicitly rebind the spec.",
    "DECISION_RECORD_INVALID": "Repair the invalid decision record before resuming.",
    "ENVELOPE_INVALID": "Repair the invalid report before resuming.",
    "COMMAND_FAILED": "Inspect the isolated runtime and repository contract.",
}


class SddCommandError(ProjectError):
    def __init__(self, cli_code: str, detail: str):
        self.cli_code = cli_code
        super().__init__(422, detail, code=f"SDD_{cli_code}")


async def command(*args: str, cwd: Path, env: dict | None = None, allow_failure: bool = False) -> str:
    if args[0] in ("devkit", "git-safe"):
        from .isolation import isolated_command
        from .runtime import runtime_home, runtime_pin

        home, pin = runtime_home(), runtime_pin()
        temp = cwd / ".devkit/transient/hub-tmp"
        temp.mkdir(parents=True, exist_ok=True)
        invocation = isolated_command(home, cwd, args[1:], pin["python_prefix"], git=args[0] == "git-safe")
        return await _command(
            *invocation,
            cwd=cwd,
            env={
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "TMPDIR": str(temp),
                "HOME": str(temp),
                "LANG": "C.UTF-8",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            },
            allow_failure=allow_failure,
            devkit=True,
        )
    return await _command(*args, cwd=cwd, env=env, allow_failure=allow_failure)


async def _command(*args: str, cwd: Path, env: dict | None, allow_failure: bool, devkit: bool = False) -> str:
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=devkit,
    )
    try:
        async with asyncio.timeout(25):
            stdout, _stderr = await process.communicate()
    except BaseException:
        if process.returncode is None:
            if devkit:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        await process.wait()
        raise
    if process.returncode and not allow_failure:
        if devkit:
            try:
                result = json.loads(stdout)
                errors = result.get("errors") or [result.get("error") or {}]
                code = errors[0].get("code", "COMMAND_FAILED")
                if process.returncode == 1 and result.get("violations") and not result.get("errors"):
                    code = "RULES_VIOLATIONS"
            except (ValueError, KeyError, IndexError, AttributeError, TypeError):
                code = "COMMAND_FAILED"
            # Repository messages and stderr are not trusted for display (may contain secrets/paths).
            fix = CLI_FIXES.get(code, CLI_FIXES["COMMAND_FAILED"])
            raise SddCommandError(
                code if code in CLI_FIXES else "COMMAND_FAILED",
                f"SDD evaluation failed ({code if code in CLI_FIXES else 'COMMAND_FAILED'}). {fix}",
            )
        raise ProjectError(
            422,
            "Git checkout failed; check repository access and the requested commits",
            code="SDD_CHECKOUT_FAILED",
        )
    return stdout.decode() if not process.returncode else ""


@asynccontextmanager
async def checkout(repository: str, head: str, base: str, token: str):
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (head, base)):
        raise ProjectError(422, "SDD requires exact Git head and base commits")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ProjectError(422, "Invalid repository")
    with TemporaryDirectory(prefix="autohub-sdd-") as directory:
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
        for directory_name in (".devkit", "specs", "docs"):
            directory_path = root / directory_name
            for path in [directory_path, *directory_path.rglob("*")]:
                if path.is_symlink():
                    raise ProjectError(422, "SDD evaluation does not accept symlinked harness or evidence files")
        yield root
