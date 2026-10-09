from typing import Annotated

from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends

from .services import FlowService


class FlowUseCase:
    def __init__(self, service: Annotated[FlowService, Depends()]):
        self.service = service

    async def register(self, provider, environment, release_id, data, principal):
        async with AsyncTransaction() as session:
            return await self.service.register(session, provider, environment, release_id, data, principal)

    async def activate(self, provider, environment, release_id, data, principal):
        async with AsyncTransaction() as session:
            return await self.service.activate(
                session, provider, environment, release_id, data.expected_revision, principal
            )

    async def start(self, data, principal):
        async with AsyncTransaction() as session:
            return await self.service.start(session, data, principal)

    async def get(self, run_id, principal):
        async with AsyncTransaction() as session:
            return await self.service.read(session, await self.service.get(session, run_id, principal))

    async def command(self, run_id, data, principal):
        async with AsyncTransaction() as session:
            return await self.service.command(session, run_id, data, principal)
