"""Install a lock-derived SDD runtime so that no repository code meets a credential or the network.

The Hub process fetches GitHub sources with the project's connector token and installs hashed registry wheels
(installing a wheel runs no package code). Each Git source is then built offline inside the OS sandbox with the
image's pinned build backend, and the built wheels are installed offline. A finished staging directory is published
atomically as the cache entry with its ``pin.json``.
"""

import asyncio
import json
import os
import re
import shutil
import signal
from contextlib import suppress
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError

from . import runtime_cache as cache
from .checkout import credential_env, remote_url
from .isolation import isolated_build, isolated_python
from .lock_runtime import Selection, build_home, interpreter, uv_binary

FETCH_TIMEOUT = 180
INSTALL_TIMEOUT = 600
BUILD_TIMEOUT = 300
PROBE_TIMEOUT = 60
INVENTORY = (
    "import json,sys\n"
    "from importlib.metadata import distributions, entry_points\n"
    "print(json.dumps({'python_prefix': sys.base_prefix,"
    " 'packages': {d.metadata['Name'].lower(): d.version for d in distributions()},"
    " 'bundles': sorted({ep.name for ep in entry_points(group='devkit.bundles')})}))\n"
)


class InstallFailure(Exception):
    """A failed install step, carrying only a catalog code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _plain_env(home: Path) -> dict:
    """The environment of every install subprocess: no inherited credentials or user configuration."""
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(home),
        "TMPDIR": str(home),
        "LANG": "C.UTF-8",
        "UV_NO_CONFIG": "1",
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_CACHE_DIR": str(home / ".uv-cache"),
        "NO_COLOR": "1",
    }


async def run(args: list[str], *, cwd: Path, env: dict, timeout: int, code: str, group: bool = False) -> str:
    """Run one step; any failure becomes ``code`` without exposing stderr, URLs or credentials."""
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=group,
        )
    except OSError:
        raise InstallFailure(code) from None
    try:
        async with asyncio.timeout(timeout):
            stdout, _ = await process.communicate()
    except BaseException as exc:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                if group:
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            await process.wait()
        if isinstance(exc, TimeoutError):
            raise InstallFailure(code) from None
        raise  # cancellation of the install itself (shutdown) propagates
    if process.returncode:
        raise InstallFailure(code)
    return stdout.decode(errors="replace")


async def fetch_sources(selection: Selection, staged: Path, token: str) -> dict[str, Path]:
    """Hub-process shallow fetches of each locked GitHub revision; the token never reaches a sandbox."""
    trees: dict[tuple[str, str], Path] = {}
    packages: dict[str, Path] = {}
    env = {**credential_env(token), "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(staged)}
    for source in selection.git:
        key = (source.repository, source.revision)
        if key not in trees:
            tree = staged / "src" / re.sub(r"[^A-Za-z0-9._-]", "_", f"{source.repository}-{source.revision}")
            tree.mkdir(parents=True)
            git = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]
            await run([*git, "init", "-q"], cwd=tree, env=env, timeout=FETCH_TIMEOUT, code="SDD_RUNTIME_INSTALL_FAILED")
            await run(
                [*git, "fetch", "-q", "--depth", "1", "--no-tags", remote_url(source.repository), source.revision],
                cwd=tree,
                env=env,
                timeout=FETCH_TIMEOUT,
                code="SDD_RUNTIME_SOURCE_UNAVAILABLE",
            )
            await run(
                [*git, "checkout", "-q", "--detach", "FETCH_HEAD"],
                cwd=tree,
                env=env,
                timeout=FETCH_TIMEOUT,
                code="SDD_RUNTIME_INSTALL_FAILED",
            )
            trees[key] = tree
        directory = (trees[key] / source.subdirectory).resolve() if source.subdirectory else trees[key]
        if not directory.is_relative_to(trees[key]) or not (directory / "pyproject.toml").is_file():
            raise InstallFailure("SDD_RUNTIME_INSTALL_FAILED")
        packages[source.package] = directory
    return packages


async def install_wheels(selection: Selection, staged: Path) -> Path:
    """Create the venv with the image interpreter and add hashed registry wheels (no package code runs)."""
    env, uv = _plain_env(staged), uv_binary()
    venv = staged / ".venv"
    await run(
        [uv, "venv", "-q", "--python", str(interpreter()), str(venv)],
        cwd=staged,
        env=env,
        timeout=PROBE_TIMEOUT,
        code="SDD_RUNTIME_INSTALL_FAILED",
    )
    if selection.registry:
        requirements = staged / "registry.txt"
        requirements.write_text("\n".join(selection.registry) + "\n")
        await run(
            [uv, "pip", "install", "-q", "--python", str(venv / "bin/python"), "--no-deps", "--only-binary", ":all:"]
            + ["--require-hashes", "-r", str(requirements)],
            cwd=staged,
            env=env,
            timeout=INSTALL_TIMEOUT,
            code="SDD_RUNTIME_INSTALL_FAILED",
        )
    return venv


async def build_sources(packages: dict[str, Path], staged: Path, venv: Path) -> None:
    """Build each source offline in the sandbox with the pinned backend, then install the wheels offline."""
    if not packages:
        return
    build_python = build_home() / ".venv/bin/python"
    uv = Path(shutil.which(uv_binary()) or uv_binary()).resolve()
    if not build_python.exists():
        raise InstallFailure("SDD_RUNTIME_INSTALL_FAILED")
    wheels = staged / "wheels"
    wheels.mkdir()
    env = {**_plain_env(staged), "UV_OFFLINE": "1"}
    for directory in packages.values():
        args = ("build", "-q", "--wheel", "--offline", "--no-build-isolation", "--python", str(build_python))
        args += ("--out-dir", str(wheels), str(directory))
        await run(
            isolated_build(staged, build_python, uv, args),
            cwd=staged,
            env=env,
            timeout=BUILD_TIMEOUT,
            code="SDD_RUNTIME_INSTALL_FAILED",
            group=True,
        )
    built = sorted(str(path) for path in wheels.glob("*.whl"))
    if len(built) != len(packages):
        raise InstallFailure("SDD_RUNTIME_INSTALL_FAILED")
    await run(
        [uv_binary(), "pip", "install", "-q", "--python", str(venv / "bin/python"), "--offline", "--no-deps"]
        + ["--no-index", *built],
        cwd=staged,
        env=env,
        timeout=INSTALL_TIMEOUT,
        code="SDD_RUNTIME_INSTALL_FAILED",
    )


async def write_pin(selection: Selection, staged: Path, venv: Path) -> dict:
    """Probe the new venv inside the sandbox and record an identity-only pin (no paths beyond the prefix)."""
    output = await run(
        isolated_python(staged, venv / "bin/python", str(Path(os.path.realpath(interpreter())).parent.parent), INVENTORY),
        cwd=staged,
        env=_plain_env(staged),
        timeout=PROBE_TIMEOUT,
        code="SDD_RUNTIME_INSTALL_FAILED",
        group=True,
    )
    try:
        inventory = json.loads(output)
    except ValueError:
        raise InstallFailure("SDD_RUNTIME_INSTALL_FAILED") from None
    if "devkit-spec" not in inventory.get("packages", {}):
        raise InstallFailure("SDD_RUNTIME_INSTALL_FAILED")
    pin = {
        "provider": "devkit-spec",
        "identity": selection.identity,
        "lock_sha256": selection.identity,
        "group": selection.group,
        "python": selection.python,
        "python_prefix": inventory["python_prefix"],
        "packages": {k: v for k, v in sorted(inventory["packages"].items()) if k.startswith("devkit")},
        "bundles": inventory.get("bundles", []),
        "revisions": {source.package: source.revision for source in sorted(selection.git, key=lambda s: s.package)},
    }
    (staged / "pin.json").write_text(json.dumps(pin, indent=2, sort_keys=True) + "\n")
    return pin


def _clean(staged: Path) -> None:
    for name in ("src", "wheels", ".uv-cache", "registry.txt"):
        path = staged / name
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


async def install(selection: Selection, token: str) -> Path:
    """Build the runtime for ``selection`` into a staging directory and publish it; the caller holds the claim."""
    staged = cache.staging(selection.identity)
    try:
        packages = await fetch_sources(selection, staged, token)
        venv = await install_wheels(selection, staged)
        await build_sources(packages, staged, venv)
        await write_pin(selection, staged, venv)
        _clean(staged)
        target = cache.publish(selection.identity, staged)
    except BaseException:
        shutil.rmtree(staged, ignore_errors=True)
        raise
    cache.clear_failure(selection.identity)
    cache.evict()
    return target


async def build(selection: Selection, token: str) -> bool:
    """Install once per identity across processes; record a failure code for later callers. False: claimed elsewhere."""
    claim = cache.try_build_lock(selection.identity)
    if claim is None:
        return False
    try:
        if not cache.complete(selection.identity):
            await install(selection, token)
    except InstallFailure as exc:
        cache.record_failure(selection.identity, exc.code)
    except ProjectError as exc:  # no isolation runner: the same refusal later callers will see
        cache.record_failure(selection.identity, exc.code or "SDD_RUNTIME_INSTALL_FAILED")
    finally:
        claim.release()
    return True
