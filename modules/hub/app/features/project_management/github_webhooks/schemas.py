from datetime import datetime
from typing import Literal

from app_layer_base.base.schemas.mixin import TimestampSchemaMixin, UUIDSchemaMixin
from pydantic import BaseModel, ConfigDict

WebhookDeliveryStatus = Literal["received", "retrying", "processed", "failed"]


class GitHubWebhookDeliveryRead(UUIDSchemaMixin, TimestampSchemaMixin):
    model_config = ConfigDict(from_attributes=True)

    delivery_id: str
    event: str
    repository: str | None
    pull_number: int | None
    auto_run: bool
    requested_catalog: str | None
    status: str
    attempts: int
    processed_at: datetime | None
    # Why a trigger did not enroll or dispatch, or that processing failed; empty for an ordinary delivery.
    failure_detail: str | None


class GitHubWebhookDeliveryList(BaseModel):
    items: list[GitHubWebhookDeliveryRead]
    total_count: int
