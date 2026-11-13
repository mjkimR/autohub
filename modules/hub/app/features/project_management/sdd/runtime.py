"""The devkit runtime of the checked-out commit, installed from its own uv.lock and resolved on first use.

A checkout scope registers its root and the project's connector token; nothing is selected or installed until a
devkit command needs it, so Git-only operations never wait for a runtime. A complete cache entry is leased for the
rest of the scope. A missing entry starts one background install per identity, which a caller's deadline cannot
cancel, and the caller receives a retryable ``SDD_RUNTIME_PREPARING`` refusal meanwhile.
"""

import asyncio
import json
import re
import tomllib
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError

from . import runtime_cache as cache
from .lock_runtime import Selection, select

RECEIPT_STALE_DETAIL = (
    "The committed devkit receipt, configuration or seeded files are out of date for the repository's locked "
    "devkit{revision}; Hub regenerated the managed assets for this evaluation. Run devkit sync with the locked "
    "devkit-spec and commit the result before integration (a receipt change needs a new enrollment)."
)
FAILURES = {
    "SDD_RUNTIME_SOURCE_UNAVAILABLE": (
        "The project's GitHub connector cannot read a Git source the repository locks for devkit; grant it read "
        "access and retry."
    ),
    "SDD_RUNTIME_INSTALL_FAILED": (
        "Hub could not install the repository's locked devkit runtime; check that registry packages provide wheels "
        "and Git sources build with the provided backend, then retry."
    ),
    "SDD_ISOLATION_UNAVAILABLE": "SDD evaluation requires an isolated runner (bubblewrap on Linux, sandbox-exec on macOS)",
}
PREPARING = "Hub is installing the repository's locked devkit runtime; retry shortly."


@dataclass
class RuntimeSource:
    root: Path
    token: str | None
    home: Path | None = None
    stack: ExitStack = field(default_factory=ExitStack)


_source: ContextVar[RuntimeSource | None] = ContextVar("sdd_runtime_source", default=None)
_installs: dict[str, asyncio.Task] = {}


@contextmanager
def runtime_source(root: Path, token: str | None):
    """Make ``root``'s locked runtime available to devkit commands in this scope; leases end with it."""
    source = RuntimeSource(Path(root).resolve(), token)
    marker = _source.set(source)
    try:
        yield source
    finally:
        _source.reset(marker)
        source.stack.close()


def current_source() -> RuntimeSource:
    source = _source.get()
    if source is None:
        raise ProjectError(503, "No checkout scope selects an SDD runtime", code="SDD_RUNTIME_UNAVAILABLE")
    return source


def _start_install(selection: Selection, token: str | None) -> None:
    """One process-level install task per identity; it is not awaited, so no caller can cancel it."""
    from .runtime_install import build

    task = _installs.get(selection.identity)
    if task is not None and not task.done():
        return
    _installs[selection.identity] = asyncio.get_running_loop().create_task(build(selection, token or ""))


def install_task(identity: str) -> asyncio.Task | None:
    return _installs.get(identity)


async def resolve(source: RuntimeSource, *, start: bool = True) -> tuple[Selection, str]:
    """The selection and its cache state (``ready``, ``preparing`` or a failure code); may start an install."""
    selection = await asyncio.to_thread(select, source.root)
    if cache.complete(selection.identity):
        return selection, "ready"
    if code := cache.failure(selection.identity):
        return selection, code
    if start:
        _start_install(selection, source.token)
    return selection, "preparing"


async def ensure_runtime() -> Path:
    """The leased cache entry of the current checkout's runtime, or a refusal naming why it is unavailable."""
    source = current_source()
    if source.home is not None:
        return source.home
    selection, state = await resolve(source)
    if state == "preparing":
        raise ProjectError(503, PREPARING, code="SDD_RUNTIME_PREPARING")
    if state != "ready":
        raise ProjectError(422, FAILURES.get(state, FAILURES["SDD_RUNTIME_INSTALL_FAILED"]), code=state)
    source.home = source.stack.enter_context(cache.lease(selection.identity))
    if not cache.complete(selection.identity):  # evicted between the check and the lease
        source.stack.close()
        source.stack = ExitStack()
        source.home = None
        raise ProjectError(503, PREPARING, code="SDD_RUNTIME_PREPARING")
    return source.home


def runtime_home() -> Path:
    source = _source.get()
    if source is None or source.home is None:
        raise ProjectError(503, "The SDD runtime has not been resolved", code="SDD_RUNTIME_UNAVAILABLE")
    return source.home


def runtime_pin() -> dict:
    home = runtime_home()
    try:
        pin = json.loads((home / "pin.json").read_text())
        if pin["provider"] != "devkit-spec" or pin["identity"] != home.name:
            raise ValueError("runtime pin mismatch")
        return pin
    except (OSError, ValueError, KeyError, TypeError):
        raise ProjectError(422, "The cached SDD runtime is inconsistent; retry", code="SDD_RUNTIME_UNAVAILABLE") from None


def runtime_identity() -> dict:
    """The deterministic identity record compared by batches: no paths, times or cache locations."""
    pin = runtime_pin()
    return {
        "provider": pin["provider"],
        "identity": pin["identity"],
        "python": pin.get("python"),
        "revisions": dict(sorted((pin.get("revisions") or {}).items())),
    }


def configured_version() -> str:
    return "devkit-lock:" + runtime_pin()["identity"]


async def restore(root: Path) -> list[dict]:
    """Restore the Git-ignored managed assets of a checkout from its locked runtime; report a stale receipt.

    ``devkit sync --locked`` restores exactly what the committed receipt records. When that receipt no longer
    matches the locked packages (``RECEIPT_STALE``), the assets are regenerated with a plain ``devkit sync``
    instead and the mismatch is returned as a warning: the checkout is disposable, so the repository's commits
    stay untouched. Every other failure blocks.
    """
    from .checkout import SddCommandError, command

    if not (root / ".devkit/installation.json").is_file():
        raise ProjectError(
            422, "Commit the devkit configuration and installation receipt before enrolling", code="SDD_RECEIPT_MISSING"
        )
    await ensure_runtime()
    check_bundles(root)
    try:
        await command("devkit", "sync", "--locked", "--format", "json", cwd=root)
    except SddCommandError as exc:
        if exc.cli_code != "RECEIPT_STALE":
            raise
        await command("devkit", "sync", "--format", "json", cwd=root)
        return [stale_warning()]
    return []


def stale_warning() -> dict:
    """The RECEIPT_STALE warning, naming the locked devkit-spec revision when the pin records one."""
    try:
        revisions = runtime_pin().get("revisions")
    except ProjectError:
        revisions = None
    revision = revisions.get("devkit-spec") if isinstance(revisions, dict) else None
    named = f" (devkit-spec {str(revision)[:12]})" if isinstance(revision, str) and revision else ""
    return {"code": "RECEIPT_STALE", "detail": RECEIPT_STALE_DETAIL.format(revision=named)}


def check_bundles(root: Path) -> None:
    """Refuse bundles that no installed package of the repository's own lock provides, before sync."""
    config = root / ".devkit/config.toml"
    if not config.is_file():
        return  # sync reports malformed/missing configuration
    try:
        presets = tomllib.loads(config.read_text()).get("presets", {})
        receipt = json.loads((root / ".devkit/installation.json").read_text())
        required = {name for name, value in presets.items() if value is not False}
        required.update(row["bundle"] for row in receipt.get("assets", []) if isinstance(row.get("bundle"), str))
    except (ValueError, TypeError, KeyError, AttributeError):
        return  # the CLI owns full configuration/receipt validation
    missing = sorted(required - set(runtime_pin().get("bundles") or []))
    if missing:
        # Only bundle identifiers, never arbitrary repository text, enter diagnostics.
        names = [name for name in missing if re.fullmatch(r"[a-z][a-z0-9-]{0,63}", name)]
        raise ProjectError(
            422,
            f"The repository's locked devkit runtime is missing bundles: {', '.join(names) or 'invalid selection'}. "
            "Add the packages providing them to the locked devkit dependency group and commit uv.lock.",
            code="SDD_BUNDLES_MISSING",
        )
