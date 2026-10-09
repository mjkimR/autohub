from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeliveryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: str = Field(pattern=r"^[a-z][a-z0-9_-]*$", max_length=64)
    environment: str = Field(pattern=r"^[a-z][a-z0-9_-]*$", max_length=64)
    project_id: UUID
    checkout: Path

    @field_validator("checkout")
    @classmethod
    def absolute_checkout(cls, value):
        if not value.is_absolute():
            raise ValueError("delivery checkout must be an absolute server path")
        return value

    def snapshot(self):
        return self.model_dump(mode="json")
