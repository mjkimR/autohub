from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InteractionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    expected_revision: int = Field(ge=1)


class QuestionWrite(InteractionWrite):
    question: str = Field(min_length=1, max_length=8000)

    @field_validator("question")
    @classmethod
    def no_agent_trigger(cls, value: str) -> str:
        from app.features.project_management.pipeline_runs.dispatch import CODEX_MENTION

        if CODEX_MENTION.search(value) or "<!--" in value:
            raise ValueError("Omit agent mentions and hidden markers from the question")
        return value


class AnswerWrite(InteractionWrite):
    answer: str = Field(min_length=1, max_length=8000)

    @field_validator("answer")
    @classmethod
    def no_agent_trigger(cls, value: str) -> str:
        from app.features.project_management.pipeline_runs.dispatch import CODEX_MENTION

        if CODEX_MENTION.search(value) or "<!--" in value:
            raise ValueError("Omit agent mentions and hidden markers from the answer")
        return value


class QuestionDismiss(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2000)


class ResumeRunRequest(InteractionWrite):
    answer_id: UUID | None = None


class AnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    question_id: UUID
    answer: str
    actor: str
    created_at: datetime
    applied_attempt_id: UUID | None


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    pipeline_run_id: UUID
    execution_attempt_id: UUID | None
    head_sha: str
    question: str
    actor: str
    source: str
    state: str
    resolution: str | None
    created_at: datetime
    answers: list[AnswerRead] = Field(default_factory=list)


class QuestionList(BaseModel):
    items: list[QuestionRead]
    total_count: int
    run_revision: int
