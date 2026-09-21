from typing import Annotated

from app.features.dashboard.repos import DashboardRepository
from app.features.dashboard.schemas import DashboardStats
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends


class DashboardUseCase:
    def __init__(self, repo: Annotated[DashboardRepository, Depends()]):
        self.repo = repo

    async def stats(self) -> DashboardStats:
        async with AsyncTransaction() as session:
            return await self.repo.stats(session)
