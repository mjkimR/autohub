from typing import Annotated

from app.features.dashboard.schemas import DashboardStats
from app.features.dashboard.usecases import DashboardUseCase
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(use_case: Annotated[DashboardUseCase, Depends()]):
    return await use_case.stats()
