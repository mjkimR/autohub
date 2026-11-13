"""Read retained batch history and settle local future-admission ownership."""

from typing import Annotated

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends

from .batch_models import SddBatchControl
from .batch_policy import same_request
from .batch_repo import BatchRepository
from .usecases import SddUseCase


class SddBatchUseCase:
    def __init__(self, projects: Annotated[ProjectService, Depends()], sdd: Annotated[SddUseCase, Depends()]):
        self.projects, self.sdd, self.repo = projects, sdd, BatchRepository()

    async def _read(self, session, row):
        return {
            "retired": True,
            "id": str(row.id),
            "project_id": str(row.project_id),
            "state": row.state,
            "revision": row.revision,
            "exclusion": row.exclusion,
            "detail": row.detail,
            "basis": row.basis,
            "evaluation": row.evaluation,
            "members": [
                {
                    "id": str(m.id),
                    "anchor_id": m.anchor_id,
                    "path": m.path,
                    "position": m.position,
                    "initial": m.initial,
                    "phase": m.phase,
                    "state": m.state,
                    "spec_anchor": m.spec_anchor,
                    "outcome": m.outcome,
                    "claims": [
                        {
                            "id": str(c.id),
                            "activity": c.activity,
                            "settled": c.settled,
                            "uncertain": bool(c.checkpoint.get("uncertain")),
                            "uncertainty_reason": c.checkpoint.get("last_error")
                            if c.checkpoint.get("uncertain")
                            else None,
                            "uncertainty_observed_at": c.checkpoint.get("uncertainty_observed_at"),
                            "branch": c.checkpoint.get("branch"),
                            "initial_sha": c.checkpoint.get("initial_sha"),
                            "pull_number": c.checkpoint.get("pull_number"),
                            "run_id": str(c.run_id) if c.run_id else c.checkpoint.get("run_id"),
                        }
                        for c in await self.repo.claims(session, m.id)
                    ],
                }
                for m in await self.repo.members(session, row.id)
            ],
        }

    async def get(self, project_id, batch_id):
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id)
            row = await self.repo.get(session, project_id, batch_id)
            if row is None:
                raise ProjectError(404, "SDD batch not found")
            return await self._read(session, row)

    async def lists(self, project_id):
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id)
            return [await self._read(session, row) for row in await self.repo.lists(session, project_id)]

    async def create(self, project_id, request, actor):
        return await self.sdd.retired_operation(project_id)

    async def control(self, project_id, batch_id, request, actor):
        if request.action != "stop":
            return await self.sdd.retired_operation(project_id)
        digest = request_digest(request.model_dump(mode="json"))
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id, lock=True)
            row = await self.repo.get(session, project_id, batch_id, lock=True)
            if row is None:
                raise ProjectError(404, "SDD batch not found")
            previous = await self.repo.receipt(session, batch_id, request.request_id)
            if previous:
                same_request(previous, actor, digest)
                return await self._read(session, row)
            if row.revision != request.expected_revision:
                raise ProjectError(409, "Batch revision changed; inspect retained history")
            row.state = "stopped"
            row.revision += 1
            row.detail = "Native batch execution retired; Stop settles local future admission only"
            members = await self.repo.members(session, row.id)
            claims = [c for m in members for c in await self.repo.claims(session, m.id)]
            if not any(not c.settled for c in claims):
                row.exclusion = False
            await self.repo.save(
                session,
                SddBatchControl(
                    batch_id=batch_id,
                    request_id=request.request_id,
                    actor=actor,
                    request_digest=digest,
                    action="stop",
                ),
            )
            return await self._read(session, row)
