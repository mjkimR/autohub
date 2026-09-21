"""Read a connector token with explicit transaction ownership."""

from typing import Annotated
from uuid import UUID

from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, EncryptedCredentials
from app.features.configuration.connectors.errors import ConnectorTokenError
from app.features.configuration.connectors.repos import ConnectorRepository
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends


class ReadConnectorTokenUseCase:
    def __init__(
        self, repo: Annotated[ConnectorRepository, Depends()], cipher: Annotated[ConnectorCredentialCipher, Depends()]
    ):
        self.repo = repo
        self.cipher = cipher

    async def execute(self, connector_id: UUID, expected_provider: str) -> str:
        async with AsyncTransaction() as session:
            connector = await self.repo.get_by_pk(session, connector_id)
            if connector is None or not connector.enabled or connector.provider != expected_provider:
                raise ConnectorTokenError(f"An enabled {expected_provider} connector is required")
            provider = connector.provider
            encrypted = EncryptedCredentials(
                connector.credentials_ciphertext, connector.credentials_nonce, connector.credential_key_version
            )
        # A key provider can use external I/O. Only copied ciphertext crosses the transaction boundary.
        credentials = await self.cipher.decrypt(connector_id, provider, encrypted)
        token = credentials.get("token")
        if not isinstance(token, str) or not token.strip():
            raise ConnectorTokenError(f"{expected_provider} connector credentials must contain a non-empty token")
        return token
