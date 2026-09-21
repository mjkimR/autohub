from typing import Annotated

from app.features.execution.dispatchers.usecases.dispatch import DispatchUseCase
from app.features.execution.dispatchers.usecases.housekeeping import TickHousekeepingUseCase
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

router = APIRouter(prefix="/dispatchers", tags=["Dispatcher"], dependencies=[])


class DispatchResponse(BaseModel):
    dispatched: int


@router.post("/trigger", status_code=status.HTTP_200_OK, response_model=DispatchResponse)
async def trigger_dispatch(
    use_case: Annotated[DispatchUseCase, Depends()],
    housekeeping: Annotated[TickHousekeepingUseCase, Depends()],
):
    """Called by an external trigger such as Google Cloud Scheduler.
    Processes due schedules using FOR UPDATE SKIP LOCKED to prevent duplicate execution.
    """
    await housekeeping.record_tick()
    try:
        count = await use_case.execute()
    finally:
        # After the schedules, so a run that stopped in this tick is announced by it.
        await housekeeping.after_dispatch()
    return DispatchResponse(dispatched=count)
