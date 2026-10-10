from typing import Annotated
from uuid import UUID

from app.features.project_management.repositories.schemas import (
    RepoBlobRead,
    RepoInfoRead,
    RepoTreeRead,
)
from app.features.project_management.repositories.usecases import RepositoryUseCase
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/projects/{project_id}/repository", tags=["Repository"])


@router.get("/info", response_model=RepoInfoRead)
async def get_repository_info(
    project_id: UUID,
    use_case: Annotated[RepositoryUseCase, Depends()],
):
    """Retrieve repository information including default branch and available branches."""
    return await use_case.get_info(project_id)


@router.get("/tree", response_model=RepoTreeRead)
async def get_repository_tree(
    project_id: UUID,
    use_case: Annotated[RepositoryUseCase, Depends()],
    path: str = Query("", description="Directory path relative to repository root"),
    ref: str = Query("", description="Git branch, tag, or commit reference"),
):
    """List directory contents at the specified path and ref."""
    return await use_case.get_tree(project_id, path=path, ref=ref)


@router.get("/blob", response_model=RepoBlobRead)
async def get_repository_blob(
    project_id: UUID,
    use_case: Annotated[RepositoryUseCase, Depends()],
    path: str = Query(..., description="File path relative to repository root"),
    ref: str = Query("", description="Git branch, tag, or commit reference"),
):
    """Retrieve raw file content and metadata at the specified path and ref."""
    return await use_case.get_blob(project_id, path=path, ref=ref)
