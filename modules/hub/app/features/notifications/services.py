import uuid
from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, EncryptedCredentials
from app.features.notifications.models import NotificationChannel
from app.features.notifications.repos import NotificationChannelRepository
from app.features.notifications.schemas import NotificationChannelCreate, NotificationChannelPatch
from app.features.project_management.projects.services import ProjectError
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


def _sealing_scope(kind: str) -> str:
    # Binds the sealed secret to a notification channel, so it can never be replayed as a connector's.
    return f"notification:{kind}"


class NotificationChannelService:
    def __init__(
        self,
        repo: Annotated[NotificationChannelRepository, Depends()],
        cipher: Annotated[ConnectorCredentialCipher, Depends()],
    ) -> None:
        self.repo = repo
        self.cipher = cipher

    async def list(self, session: AsyncSession) -> Sequence[NotificationChannel]:
        return await self.repo.list(session)

    async def create(self, session: AsyncSession, data: NotificationChannelCreate) -> NotificationChannel:
        if await self.repo.get_by_name(session, data.name) is not None:
            raise ProjectError(409, "Notification channel name must be unique")
        channel_id = uuid.uuid4()
        sealed = await self.cipher.encrypt(channel_id, _sealing_scope(data.kind), {"token": data.bot_token.strip()})
        channel = NotificationChannel(
            id=channel_id,
            name=data.name,
            kind=data.kind,
            enabled=data.enabled,
            config={"chat_id": data.chat_id.strip()},
            credentials_ciphertext=sealed.ciphertext,
            credentials_nonce=sealed.nonce,
            credential_key_version=sealed.key_version,
        )
        session.add(channel)
        await session.flush()
        return channel

    async def patch(
        self, session: AsyncSession, channel_id: UUID, data: NotificationChannelPatch
    ) -> NotificationChannel:
        channel = await self._require(session, channel_id, lock=True)
        if data.name is not None and data.name != channel.name:
            if await self.repo.get_by_name(session, data.name) is not None:
                raise ProjectError(409, "Notification channel name must be unique")
            channel.name = data.name
        if data.enabled is not None:
            channel.enabled = data.enabled
        if data.chat_id is not None:
            channel.config = {**(channel.config or {}), "chat_id": data.chat_id.strip()}
        if data.bot_token is not None:
            sealed = await self.cipher.encrypt(
                channel.id, _sealing_scope(channel.kind), {"token": data.bot_token.strip()}
            )
            channel.credentials_ciphertext = sealed.ciphertext
            channel.credentials_nonce = sealed.nonce
            channel.credential_key_version = sealed.key_version
        await session.flush()
        return channel

    async def delete(self, session: AsyncSession, channel_id: UUID) -> None:
        await session.delete(await self._require(session, channel_id, lock=True))
        await session.flush()

    async def bot_token(self, channel: NotificationChannel) -> str:
        credentials = await self.cipher.decrypt(
            channel.id,
            _sealing_scope(channel.kind),
            EncryptedCredentials(
                ciphertext=channel.credentials_ciphertext,
                nonce=channel.credentials_nonce,
                key_version=channel.credential_key_version,
            ),
        )
        return str(credentials.get("token") or "")

    async def _require(self, session: AsyncSession, channel_id: UUID, *, lock: bool = False) -> NotificationChannel:
        channel = await self.repo.get(session, channel_id, lock=lock)
        if channel is None:
            raise ProjectError(404, "Notification channel not found")
        return channel
