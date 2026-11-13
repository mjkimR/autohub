"""Install a lock-derived SDD runtime so that no repository code meets a credential, the network or the Hub process.

The Hub process fetches GitHub sources with the project's connector token into ``work/`` and installs hashed
registry wheels into a fresh venv (installing a wheel runs no package code, and the venv's interpreter is not run
again outside a sandbox afterwards). Each Git source is then built offline in an OS sandbox that can write only
``work/``, with the image's pinned build backend; the built wheels are installed offline in a sandbox, and the
inventory is probed in one. The Hub process writes ``pin.json`` from values it computes itself and publishes the
staging directory atomically as the cache entry.
"""

import asyncio
import json
import logging
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


logger = logging.getLogger(__name__)
WORK = "work"  # the only directory repository build code may write


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
            name = re.sub(r"[^A-Za-z0-9._-]", "_", f"{source.repository}-{source.revision}")
            tree = staged / WORK / "src" / name
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
    """Create the venv with the image interpreter and add hashed registry wheels (no package code runs).

    This is the last Hub-process use of the venv's interpreter: once a package is installed, a ``.pth`` file could
    run when an interpreter is queried, so later steps that touch the venv run inside the sandbox.
    """
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
        args = [uv, "pip", "install", "-q", "--python", str(venv / "bin/python"), "--no-deps"]
        args += ["--only-binary", ":all:", "--require-hashes", "-r", str(requirements)]
        await run(args, cwd=staged, env=env, timeout=INSTALL_TIMEOUT, code="SDD_RUNTIME_INSTALL_FAILED")
    return venv


def built_wheels(staged: Path, expected: int) -> list[str]:
    """The regular wheel files the builds produced; a symlink anywhere on the way is refused."""
    wheels = staged / WORK / "wheels"
    if (staged / WORK).is_symlink() or wheels.is_symlink() or not wheels.is_dir():
        raise InstallFailure("SDD_RUNTIME_INSTALL_FAILED")
    built = sorted(path for path in wheels.iterdir() if path.name.endswith(".whl"))
    if len(built) != expected or any(path.is_symlink() or not path.is_file() for path in built):
        raise InstallFailure("SDD_RUNTIME_INSTALL_FAILED")
    return [str(path) for path in built]


async def build_sources(packages: dict[str, Path], staged: Path, venv: Path) -> None:
    """Build each source offline in a sandbox that writes only ``work/``; install the wheels in a sandbox too."""
    if not packages:
        return
    build_python = build_home() / ".venv/bin/python"
    uv = Path(shutil.which(uv_binary()) or uv_binary()).resolve()
    if not build_python.exists():
        raise InstallFailure("SDD_RUNTIME_INSTALL_FAILED")
    work = staged / WORK
    (work / "wheels").mkdir()
    (work / "home").mkdir()
    build_env = {**_plain_env(work / "home"), "UV_OFFLINE": "1"}
    for directory in packages.values():
        args = ("build", "-q", "--wheel", "--offline", "--no-build-isolation", "--python", str(build_python))
        args += ("--out-dir", str(work / "wheels"), str(directory))
        await run(
            isolated_build(work, build_python, uv, args),
            cwd=work,
            env=build_env,
            timeout=BUILD_TIMEOUT,
            code="SDD_RUNTIME_INSTALL_FAILED",
            group=True,
        )
    built = built_wheels(staged, len(packages))
    # The venv now holds registry packages: only a sandbox may run its interpreter.
    install_env = {**_plain_env(staged / WORK / "home"), "UV_OFFLINE": "1"}
    args = ("pip", "install", "-q", "--python", str(venv / "bin/python"), "--offline", "--no-deps", "--no-index")
    await run(
        isolated_build(staged, venv / "bin/python", uv, (*args, *built)),
        cwd=staged,
        env=install_env,
        timeout=INSTALL_TIMEOUT,
        code="SDD_RUNTIME_INSTALL_FAILED",
        group=True,
    )


def _inventory(output: str) -> dict:
    try:
        inventory = json.loads(output)
    except ValueError:
        raise InstallFailure("SDD_RUNTIME_INSTALL_FAILED") from None
    packages = inventory.get("packages") if isinstance(inventory, dict) else None
    bundles = inventory.get("bundles") if isinstance(inventory, dict) else None
    if (
        not isinstance(packages, dict)
        or not all(isinstance(k, str) and isinstance(v, str) for k, v in packages.items())
        or not isinstance(bundles, list)
        or not all(isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,63}", name) for name in bundles)
        or "devkit-spec" not in packages
    ):
        raise InstallFailure("SDD_RUNTIME_INSTALL_FAILED")
    return {"packages": packages, "bundles": bundles}


def _write_new(path: Path, text: str) -> None:
    """Create ``path`` without following anything a sandbox may have planted there."""
    path.unlink(missing_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(descriptor, "w") as handle:
        handle.write(text)


async def write_pin(selection: Selection, staged: Path, venv: Path) -> dict:
    """Probe the venv's inventory in the sandbox; the prefix and identity come from the Hub, never the probe."""
    prefix = str(Path(os.path.realpath(interpreter())).parent.parent)
    output = await run(
        isolated_python(staged, venv / "bin/python", prefix, INVENTORY),
        cwd=staged,
        env=_plain_env(staged / WORK / "home"),
        timeout=PROBE_TIMEOUT,
        code="SDD_RUNTIME_INSTALL_FAILED",
        group=True,
    )
    inventory = _inventory(output)
    pin = {
        "provider": "devkit-spec",
        "identity": selection.identity,
        "lock_sha256": selection.identity,
        "group": selection.group,
        "python": selection.python,
        "python_prefix": prefix,
        "packages": {k: v for k, v in sorted(inventory["packages"].items()) if k.startswith("devkit")},
        "bundles": inventory["bundles"],
        "revisions": {source.package: source.revision for source in sorted(selection.git, key=lambda s: s.package)},
    }
    _write_new(staged / "pin.json", json.dumps(pin, indent=2, sort_keys=True) + "\n")
    return pin


def _clean(staged: Path) -> None:
    for name in (WORK, ".uv-cache", "registry.txt"):
        path = staged / name
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


async def install(selection: Selection, token: str) -> Path:
    """Build the runtime for ``selection`` into a staging directory and publish it; the caller holds the claim."""
    staged = cache.staging(selection.identity)
    try:
        (staged / WORK).mkdir()
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
    await asyncio.to_thread(cache.evict)
    return target


async def build(selection: Selection, token: str) -> bool:
    """Install once per identity across processes; record a failure code for later callers. False: claimed elsewhere."""
    claim = cache.try_build_lock(selection.identity)
    if claim is None:
        return False
    scope = cache.token_scope(token)
    try:
        if not cache.complete(selection.identity):
            await install(selection, token)
    except InstallFailure as exc:
        cache.record_failure(selection.identity, exc.code, scope)
    except ProjectError as exc:  # no isolation runner: the same refusal later callers will see
        cache.record_failure(selection.identity, exc.code or "SDD_RUNTIME_INSTALL_FAILED", scope)
    except Exception as exc:  # any other failure still backs off; only its type is logged, never its text
        logger.warning("SDD runtime install failed (%s)", type(exc).__name__)
        cache.record_failure(selection.identity, "SDD_RUNTIME_INSTALL_FAILED", scope)
    finally:
        claim.release()
    return True
