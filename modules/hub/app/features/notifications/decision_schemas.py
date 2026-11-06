from datetime import datetime
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from app.features.project_management.pipeline_runs.discovery_schemas import DecisionKind
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SubscriptionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    project_scope: Literal["selected", "all"] = "selected"
    project_ids: list[UUID] = Field(default_factory=list, max_length=100)
    kinds: list[DecisionKind] = Field(default_factory=list, max_length=6)
    mode: Literal["immediate", "digest"] = "immediate"
    review_origin: str = Field(default="", max_length=500)
    trusted_destination: bool = False

    @model_validator(mode="after")
    def validate_settings(self):
        if len(set(self.project_ids)) != len(self.project_ids) or len(set(self.kinds)) != len(self.kinds):
            raise ValueError("Project and kind selections must be distinct")
        if self.enabled and (
            not self.kinds
            or not self.trusted_destination
            or (self.project_scope == "selected" and not self.project_ids)
        ):
            raise ValueError("Enablement requires kinds, selected projects and trusted destination confirmation")
        if self.review_origin:
            value = urlsplit(self.review_origin)
            try:
                loopback = value.hostname == "localhost" or ip_address(value.hostname or "").is_loopback
            except ValueError:
                loopback = False
            if (
                not value.hostname
                or value.username
                or value.password
                or value.path
                or value.query
                or value.fragment
                or not (value.scheme == "https" or (value.scheme == "http" and loopback))
            ):
                raise ValueError("Review origin must be HTTPS or loopback HTTP with no path")
            _ = value.port
        elif self.enabled:
            raise ValueError("Enabled notices require a review origin")
        return self


class SubscriptionWrite(SubscriptionSettings):
    request_id: UUID
    expected_revision: int = Field(ge=0)
    expected_destination_generation: int = Field(ge=0)


class SubscriptionRead(BaseModel):
    channel_id: UUID
    revision: int
    destination_generation: int
    settings: SubscriptionSettings
    channel_enabled: bool
    severity_enabled: bool
    chat_id: str | None
    observed_at: datetime


class NoticeResend(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    expected_revision: int = Field(ge=0)
    expected_destination_generation: int = Field(ge=0)
    acknowledge_possible_duplicate: bool = False


class NoticeAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    notice_ids: list[str]
    state: str
    created_at: datetime
    outcome_at: datetime | None
    detail: str | None


class NoticeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    decision_key: str
    fingerprint: str
    destination_generation: int
    state: str
    created_at: datetime
    observed: dict
    last_attempt_id: UUID | None


class NoticeHistory(BaseModel):
    items: list[NoticeRead]
    attempts: list[NoticeAttemptRead]
    next_cursor: str | None
    has_more: bool
    observed_at: datetime


class DecisionRequestRead(BaseModel):
    record_state: Literal["unknown", "recorded"]
    operation: Literal["subscription", "resend"]
    request_id: UUID
    result: dict | None = None
    current: SubscriptionRead
    attempt: NoticeAttemptRead | None = None
