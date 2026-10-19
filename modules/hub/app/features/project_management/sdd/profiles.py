"""Operator-owned runtime selection, scoped to one repository evaluation."""

import json
import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError

_selected: ContextVar[tuple[str, Path] | None] = ContextVar("sdd_runtime", default=None)


def selection(repository: str | None = None) -> tuple[str, Path]:
    default = ("default", Path(os.environ.get("AUTOHUB_SDD_HOME", "/opt/sdd")).resolve())
    try:
        config = json.loads(os.environ.get("AUTOHUB_SDD_PROFILES", "{}"))
        if not isinstance(config, dict) or set(config) - {"profiles", "repositories"}:
            raise ValueError
        profiles, repositories = config.get("profiles", {}), config.get("repositories", {})
        if not isinstance(profiles, dict) or not isinstance(repositories, dict):
            raise ValueError
        for name, path in profiles.items():
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", name) or name == "default":
                raise ValueError
            if not isinstance(path, str) or not Path(path).is_absolute():
                raise ValueError
        if len({repo.lower() for repo in repositories}) != len(repositories):
            raise ValueError
        for repo, name in repositories.items():
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
                raise ValueError
            if not isinstance(name, str) or (name != "default" and name not in profiles):
                raise ValueError
        name = next((v for k, v in repositories.items() if k.lower() == (repository or "").lower()), "default")
        return default if name == "default" else (name, Path(profiles[name]).resolve())
    except (ValueError, TypeError, AttributeError):
        raise ProjectError(
            422, "Configure valid server-owned SDD profiles and repository mappings", code="SDD_PROFILE_INVALID"
        ) from None


def current() -> tuple[str, Path]:
    return _selected.get() or selection()


@contextmanager
def runtime_scope(repository: str | None):
    token = _selected.set(selection(repository))
    try:
        yield
    finally:
        _selected.reset(token)
