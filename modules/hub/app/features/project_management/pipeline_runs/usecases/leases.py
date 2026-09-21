from __future__ import annotations

from datetime import timedelta
from typing import Never
from uuid import UUID, uuid4

from app.features.project_management.pipeline_runs.models import (
    PipelineRun,
)
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import (
    LeaseGrant,
    LeaseMutation,
    LeaseRequest,
)
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy.ext.asyncio import AsyncSession


async def raise_lease_conflict(repo: PipelineRunRepository, session: AsyncSession, run_id: UUID, action: str) -> Never:
    run = await repo.get(session, run_id)
    if run is None:
        raise ProjectError(404, "Pipeline run not found")
    raise ProjectError(409, f"Pipeline run lease {action} was rejected")


class PipelineRunLeases:
    def __init__(self, repo: PipelineRunRepository):
        self.repo = repo

    async def acquire_lease(self, run_id: UUID, request: LeaseRequest) -> LeaseGrant:
        now = get_current_utc_time()
        token = uuid4()
        async with AsyncTransaction() as session:
            run = await self.repo.acquire_lease(
                session,
                run_id,
                owner=request.owner,
                token=token,
                now=now,
                expires_at=now + timedelta(seconds=request.ttl_seconds),
            )
            if run is None:
                await raise_lease_conflict(self.repo, session, run_id, "acquire")
            return self._lease_grant(run)

    async def renew_lease(self, run_id: UUID, request: LeaseMutation) -> LeaseGrant:
        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            run = await self.repo.renew_lease(
                session,
                run_id,
                owner=request.owner,
                token=request.token,
                now=now,
                expires_at=now + timedelta(seconds=request.ttl_seconds),
            )
            if run is None:
                await raise_lease_conflict(self.repo, session, run_id, "renew")
            return self._lease_grant(run)

    async def release_lease(self, run_id: UUID, request: LeaseMutation) -> None:
        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            run = await self.repo.release_lease(
                session,
                run_id,
                owner=request.owner,
                token=request.token,
                now=now,
            )
            if run is None:
                await raise_lease_conflict(self.repo, session, run_id, "release")

    @staticmethod
    def _lease_grant(run: PipelineRun) -> LeaseGrant:
        if run.lease_owner is None or run.lease_token is None or run.lease_expires_at is None:
            raise RuntimeError("Lease update returned incomplete lease state")
        return LeaseGrant(
            run_id=run.id,
            owner=run.lease_owner,
            token=run.lease_token,
            expires_at=run.lease_expires_at,
            run_revision=run.revision,
        )
