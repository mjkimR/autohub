from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

OwedItemKind = Literal[
    "decision",
    "stopped-run",
    "work-plan-proposed",
    "work-item-recovery",
    "work-item-replacement",
    "work-item-attention",
    "sdd-batch-attention",
    "connection-test-cleanup",
    "failed-run",
]
OwedSubjectType = Literal[
    "decision",
    "pipeline-run",
    "work-plan",
    "work-item-recovery",
    "replacement-link",
    "work-item",
    "sdd-batch",
    "connection-test",
]
OwedActionName = Literal[
    "answer",
    "resume-run",
    "review-plan",
    "inspect-recovery",
    "accept-replacement",
    "inspect-work-item",
    "inspect-batch",
    "review-cleanup",
    "inspect-run",
]


class OwedSubject(BaseModel):
    type: OwedSubjectType
    id: str = Field(description="The subject's own ID; a decision uses its decision_key")
    project_id: UUID
    title: str | None = None


class OwedAction(BaseModel):
    name: OwedActionName = Field(description="The owner's existing action the operator takes next")
    label: str


class CatalogHold(BaseModel):
    catalog_id: UUID
    reason: Literal["unavailable", "quota-blocked"]
    available_at: datetime | None = None


class OwedContext(BaseModel):
    run_id: UUID | None = None
    work_plan_id: UUID | None = None
    work_item_id: UUID | None = None
    sdd_batch_id: UUID | None = None
    catalog_hold: CatalogHold | None = Field(default=None, description="An AI catalog hold blocking the subject")


class OwedItemRead(BaseModel):
    key: str = Field(description="<kind>:<subject id>; stable while the item stays in the set")
    kind: OwedItemKind
    counted: bool = Field(description="Whether the item carries owed-count weight; quiet items do not")
    cause: str
    subject: OwedSubject
    primary_action: OwedAction
    waiting_since: datetime
    context: OwedContext


class OwedItemPage(BaseModel):
    items: list[OwedItemRead]
    has_more: bool
    next_cursor: str | None


class OwedItemCounts(BaseModel):
    total: int = Field(description="Counted owed items the filters admit")
    by_kind: dict[OwedItemKind, int] = Field(description="Every kind, zero and quiet kinds included")
    by_project: dict[UUID, int] = Field(description="Counted owed items per project; projects with none are omitted")
