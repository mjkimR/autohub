from typing import Annotated

from app.features.scheduling.schedule_configs.models import ScheduleConfig
from app.features.scheduling.schedule_configs.schemas import (
    ScheduleConfigCreate,
    ScheduleConfigPatch,
    ScheduleConfigPut,
    ScheduleConfigRead,
)
from app.features.scheduling.schedule_configs.services import ScheduleConfigContextKwargs, ScheduleConfigService
from app_layer_base.base.schemas.paginated import PaginatedList
from app_layer_base.base.usecases.crud import (
    BaseCreateUseCase,
    BaseDeleteUseCase,
    BaseGetMultiUseCase,
    BaseGetUseCase,
    BasePatchUseCase,
    BasePutUseCase,
)
from fastapi import Depends

from ..owner_reads import ScheduleOwnerService


class GetScheduleConfigUseCase(BaseGetUseCase[ScheduleConfigService, ScheduleConfigRead, ScheduleConfigContextKwargs]):
    def __init__(self, service: Annotated[ScheduleConfigService, Depends()]) -> None:
        super().__init__(service)

    async def _execute(self, session, obj_pk, context):
        row = await self.service.get(session, obj_pk, context=context)
        return (await ScheduleOwnerService().read(session, [row]))[0] if row is not None else None


class GetMultiScheduleConfigUseCase(
    BaseGetMultiUseCase[ScheduleConfigService, ScheduleConfigRead, ScheduleConfigContextKwargs]
):
    def __init__(self, service: Annotated[ScheduleConfigService, Depends()]) -> None:
        super().__init__(service)

    async def _execute(self, session, query_options, context=None):
        page = await self.service.get_multi(session, query_options=query_options, context=context)
        return PaginatedList[ScheduleConfigRead](
            items=await ScheduleOwnerService().read(session, page.items),
            total_count=page.total_count,
            offset=page.offset,
            limit=page.limit,
        )


class CreateScheduleConfigUseCase(
    BaseCreateUseCase[ScheduleConfigService, ScheduleConfigRead, ScheduleConfigCreate, ScheduleConfigContextKwargs]
):
    def __init__(self, service: Annotated[ScheduleConfigService, Depends()]) -> None:
        super().__init__(service)

    async def _execute(self, session, obj_data, context):
        row = await self.service.create(session, obj_data, context=context)
        return (await ScheduleOwnerService().read(session, [row]))[0] if row is not None else None


class PatchScheduleConfigUseCase(
    BasePatchUseCase[
        ScheduleConfigService, ScheduleConfigRead, ScheduleConfigPut, ScheduleConfigPatch, ScheduleConfigContextKwargs
    ]
):
    def __init__(self, service: Annotated[ScheduleConfigService, Depends()]) -> None:
        super().__init__(service)

    async def _execute(self, session, obj_pk, obj_data, context):
        row = await self.service.patch(session, obj_pk, obj_data, context=context)
        return (await ScheduleOwnerService().read(session, [row]))[0] if row is not None else None


class PutScheduleConfigUseCase(
    BasePutUseCase[
        ScheduleConfigService, ScheduleConfigRead, ScheduleConfigPut, ScheduleConfigPatch, ScheduleConfigContextKwargs
    ]
):
    def __init__(self, service: Annotated[ScheduleConfigService, Depends()]) -> None:
        super().__init__(service)

    async def _execute(self, session, obj_pk, obj_data, context):
        row = await self.service.put(session, obj_pk, obj_data, context=context)
        return (await ScheduleOwnerService().read(session, [row]))[0] if row is not None else None


class DeleteScheduleConfigUseCase(
    BaseDeleteUseCase[ScheduleConfigService, ScheduleConfig, ScheduleConfigContextKwargs]
):
    def __init__(self, service: Annotated[ScheduleConfigService, Depends()]) -> None:
        super().__init__(service)
