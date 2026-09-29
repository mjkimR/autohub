"""Explicit catalogs, without process-global discovery or import-time I/O."""

from collections.abc import Iterable
from typing import Any

from .manifest import Manifest
from .pipeline import Pipeline


class Registry:
    def __init__(self, pipelines: Iterable[Pipeline[Any, Any]] = ()) -> None:
        self._pipelines: dict[tuple[str, int], Pipeline[Any, Any]] = {}
        for definition in pipelines:
            self.add(definition)

    def add(self, definition: Pipeline[Any, Any]) -> None:
        identity = (definition.key, definition.contract_version)
        if identity in self._pipelines:
            raise ValueError(f"Duplicate pipeline contract: {identity}")
        self._pipelines[identity] = definition

    def manifest(self) -> Manifest:
        """Export all definitions, sorted by key and contract version."""
        return Manifest(tasks=tuple(self._pipelines[key].spec() for key in sorted(self._pipelines)))
