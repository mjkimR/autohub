from typing import Annotated
from uuid import UUID

from app.auth import CurrentUser
from app.features.project_management.pipeline_runs.interaction_schemas import (
    AnswerRead,
    AnswerWrite,
    QuestionDismiss,
    QuestionList,
    QuestionRead,
    QuestionWrite,
)
from app.features.project_management.pipeline_runs.usecases.interactions import RunInteractionUseCase
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/pipeline-runs/{run_id}/questions", tags=["Run decisions"])
UseCase = Annotated[RunInteractionUseCase, Depends()]


@router.get("", response_model=QuestionList)
async def list_questions(
    run_id: UUID, use_case: UseCase, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    return await use_case.list(run_id, offset, limit)


@router.post("", response_model=QuestionRead)
async def ask_question(run_id: UUID, data: QuestionWrite, user: CurrentUser, use_case: UseCase):
    return await use_case.ask(run_id, data, f"user:{user.id}")


@router.post("/{question_id}/answers", response_model=AnswerRead)
async def answer_question(run_id: UUID, question_id: UUID, data: AnswerWrite, user: CurrentUser, use_case: UseCase):
    return await use_case.answer(run_id, question_id, data, f"user:{user.id}")


@router.post("/{question_id}/dismiss", response_model=QuestionRead)
async def dismiss_question(
    run_id: UUID, question_id: UUID, data: QuestionDismiss, user: CurrentUser, use_case: UseCase
):
    return await use_case.dismiss(run_id, question_id, data, f"user:{user.id}")
