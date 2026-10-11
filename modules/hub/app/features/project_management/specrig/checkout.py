"""Disposable read-only evaluation checkouts; no repository code is executed."""

import asyncio
import base64
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from app.features.project_management.projects.errors import ProjectError


async def command(*args: str, cwd: Path, env: dict | None = None, allow_failure: bool = False) -> str:
    process = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        async with asyncio.timeout(25):
            stdout, _ = await process.communicate()
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise
    if process.returncode and not allow_failure:
        raise ProjectError(422, "Specrig checkout or CLI command failed; check runner configuration and repository")
    return stdout.decode() if not process.returncode else ""


@asynccontextmanager
async def checkout(repository: str, head: str, base: str, token: str):
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (head, base)):
        raise ProjectError(422, "Specrig requires exact Git head and base commits")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ProjectError(422, "Invalid repository")
    with TemporaryDirectory(prefix="autohub-specrig-") as directory:
        root = Path(directory)
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
