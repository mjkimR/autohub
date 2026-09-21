from typing import Annotated
from uuid import UUID

from app.features.notifications.schemas import (
    NotificationChannelCreate,
    NotificationChannelList,
    NotificationChannelPatch,
    NotificationChannelRead,
    NotificationTestResult,
)
from app.features.notifications.usecases import NotificationChannelUseCase
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/notification-channels", tags=["Notification Channel"])


@router.get("", response_model=NotificationChannelList)
async def list_notification_channels(usecase: Annotated[NotificationChannelUseCase, Depends()]):
    return await usecase.list()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=NotificationChannelRead)
async def create_notification_channel(
    usecase: Annotated[NotificationChannelUseCase, Depends()], data: NotificationChannelCreate
):
    return await usecase.create(data)


@router.patch("/{channel_id}", response_model=NotificationChannelRead)
async def patch_notification_channel(
    channel_id: UUID, usecase: Annotated[NotificationChannelUseCase, Depends()], data: NotificationChannelPatch
):
    return await usecase.patch(channel_id, data)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_channel(channel_id: UUID, usecase: Annotated[NotificationChannelUseCase, Depends()]):
    await usecase.delete(channel_id)


@router.post("/{channel_id}/test", response_model=NotificationTestResult)
async def test_notification_channel(channel_id: UUID, usecase: Annotated[NotificationChannelUseCase, Depends()]):
    """Send a test notice through one channel, enabled or not, and report whether Telegram accepted it."""
    return await usecase.send_test(channel_id)
