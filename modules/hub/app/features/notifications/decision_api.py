from typing import Annotated, Literal
from uuid import UUID

from app.auth import CurrentUser
from app.features.notifications.decision_schemas import (
    DecisionRequestRead,
    NoticeHistory,
    NoticeResend,
    SubscriptionRead,
    SubscriptionWrite,
)
from app.features.notifications.decision_usecase import DecisionNoticeUseCase
from app.features.project_management.projects.errors import ProjectError
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

router = APIRouter()


async def command_result(operation):
    try:
        return await operation
    except ProjectError as error:
        code = (
            "DECISION_NOTICE_IDENTITY_CONFLICT"
            if error.code == "DECISION_NOTICE_IDENTITY_CONFLICT"
            else "DECISION_NOTICE_REFUSED"
            if error.code == "DECISION_NOTICE_REFUSED" or error.status in (409, 422)
            else "DECISION_NOTICE_UNAVAILABLE"
        )
        return JSONResponse(status_code=error.status, content={"detail": error.detail, "code": code})


@router.get("/{channel_id}/decision-subscription", response_model=SubscriptionRead)
async def read_subscription(channel_id: UUID, usecase: Annotated[DecisionNoticeUseCase, Depends()]):
    return await usecase.read(channel_id)


@router.put("/{channel_id}/decision-subscription", response_model=DecisionRequestRead)
async def save_subscription(
    channel_id: UUID, data: SubscriptionWrite, user: CurrentUser, usecase: Annotated[DecisionNoticeUseCase, Depends()]
):
    return await command_result(usecase.save(channel_id, data, f"user:{user.id}"))


@router.get("/{channel_id}/decision-notices", response_model=NoticeHistory)
async def history(
    channel_id: UUID,
    usecase: Annotated[DecisionNoticeUseCase, Depends()],
    cursor: str | None = Query(None, max_length=255),
    limit: int = Query(20, ge=1, le=100),
):
    return await usecase.history(channel_id, cursor, limit)


@router.post("/{channel_id}/decision-notices/{notice_id}/resend", response_model=DecisionRequestRead)
async def resend(
    channel_id: UUID,
    notice_id: UUID,
    data: NoticeResend,
    user: CurrentUser,
    usecase: Annotated[DecisionNoticeUseCase, Depends()],
):
    return await command_result(usecase.resend(channel_id, notice_id, data, f"user:{user.id}"))


@router.get("/{channel_id}/decision-requests/{request_id}", response_model=DecisionRequestRead)
async def request_outcome(
    channel_id: UUID,
    request_id: UUID,
    operation: Literal["subscription", "resend"],
    user: CurrentUser,
    usecase: Annotated[DecisionNoticeUseCase, Depends()],
):
    return await usecase.request(channel_id, operation, request_id, f"user:{user.id}")
