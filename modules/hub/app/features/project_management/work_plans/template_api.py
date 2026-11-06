from typing import Annotated, Literal
from uuid import UUID

from app.auth import CurrentUser
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.template_schemas import (
    TemplateCreate,
    TemplateDelete,
    TemplateFromPlan,
    TemplateList,
    TemplateOutcome,
    TemplateRegistration,
    TemplateUpdate,
    WorkPlanTemplateRead,
)
from app.features.project_management.work_plans.template_usecase import TemplateUseCase
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/projects/{project_id}/work-plan-templates", tags=["Work Plan"])
UseCase = Annotated[TemplateUseCase, Depends()]


async def command(coroutine):
    try:
        return await coroutine
    except ProjectError as error:
        return JSONResponse(
            status_code=error.status,
            content={
                "detail": error.detail,
                "code": error.code
                if error.code.startswith("TEMPLATE_")
                else "TEMPLATE_REFUSED"
                if error.status in (409, 422)
                else "TEMPLATE_ACCESS_UNAVAILABLE",
            },
        )


@router.get("", response_model=TemplateList)
async def listing(
    project_id: UUID, usecase: UseCase, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    return await usecase.list(project_id, offset, limit)


@router.post("", response_model=TemplateOutcome, status_code=201)
async def create(project_id: UUID, data: TemplateCreate, user: CurrentUser, usecase: UseCase):
    return await command(usecase.mutate(project_id, "create", None, data, f"user:{user.id}"))


@router.post("/from-plan", response_model=TemplateOutcome, status_code=201)
async def from_plan(project_id: UUID, data: TemplateFromPlan, user: CurrentUser, usecase: UseCase):
    return await command(usecase.mutate(project_id, "from-plan", data.source_plan_id, data, f"user:{user.id}"))


@router.get("/requests/{operation}/{request_id}", response_model=TemplateOutcome)
async def request(
    project_id: UUID, operation: Literal["create", "from-plan", "update", "delete"], request_id: UUID, usecase: UseCase
):
    return await usecase.read_request(project_id, operation, request_id)


@router.get("/registrations/{request_id}", response_model=TemplateOutcome)
async def registration(project_id: UUID, request_id: UUID, usecase: UseCase):
    return await usecase.read_request(project_id, "register", request_id)


@router.get("/{template_id}", response_model=WorkPlanTemplateRead)
async def get(project_id: UUID, template_id: UUID, usecase: UseCase):
    return await usecase.get(project_id, template_id)


@router.put("/{template_id}", response_model=TemplateOutcome)
async def update(project_id: UUID, template_id: UUID, data: TemplateUpdate, user: CurrentUser, usecase: UseCase):
    return await command(usecase.mutate(project_id, "update", template_id, data, f"user:{user.id}"))


@router.delete("/{template_id}", response_model=TemplateOutcome)
async def delete(project_id: UUID, template_id: UUID, data: TemplateDelete, user: CurrentUser, usecase: UseCase):
    return await command(usecase.mutate(project_id, "delete", template_id, data, f"user:{user.id}"))


@router.post("/{template_id}/registrations", response_model=TemplateOutcome, status_code=201)
async def register(
    project_id: UUID, template_id: UUID, data: TemplateRegistration, user: CurrentUser, usecase: UseCase
):
    return await command(usecase.register(project_id, template_id, data, f"user:{user.id}"))
