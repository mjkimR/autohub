"""Code-owned definitions; deployment bindings are intentionally separate."""

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PipelineSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$")
    contract_version: int = Field(gt=0, strict=True)
    title: str = Field(min_length=1)
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: Literal[1] = 1
    tasks: tuple[PipelineSpec, ...]

    def to_json(self) -> str:
        """Serialize deterministically without timestamps or environment metadata."""
        return json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
