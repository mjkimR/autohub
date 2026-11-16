"""Inspect and explicitly settle uncertain activity publication."""

from typing import Annotated

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends

from .activity_claims import lease_valid
from .claim_repo import ClaimRepository
from .schemas import ClaimRead


def claim_view(row):
    return ClaimRead(
        id=row.id,
        project_id=row.project_id,
        unit=row.unit,
        activity=row.activity,
        run_id=row.run_id,
        settled=row.settled,
        checkpoint_digest=request_digest(row.checkpoint),
        checkpoint={key: value for key, value in row.checkpoint.items() if key != "lease"},
    )


class SddClaimHistory:
    def __init__(self, projects: Annotated[ProjectService, Depends()]):
        self.projects, self.repo = projects, ClaimRepository()

    async def get(self, project_id, claim_id):
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id)
            row = await self.repo.claim(session, project_id, claim_id)
            if row is None:
                raise ProjectError(404, "Activity claim not found")
            return claim_view(row)

    async def reconcile(self, project_id, claim_id, request, actor):
        digest = request_digest(request.model_dump(mode="json"))
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id, lock=True)
            row = await self.repo.claim(session, project_id, claim_id, lock=True)
            if row is None:
                raise ProjectError(404, "Activity claim not found")
            cp = dict(row.checkpoint)
            previous = cp.get("reconciliation")
            if previous:
                if (
                    previous.get("request_id") != str(request.request_id)
                    or previous.get("actor") != actor
                    or previous.get("request_digest") != digest
                ):
                    raise ProjectError(409, "Claim reconciliation already records a different request")
                return claim_view(row)
            if row.run_id is not None or not cp.get("uncertain") or lease_valid(cp):
                raise ProjectError(
                    409,
                    "Only an uncertain activity without a Run or live lease can be settled; inspect its current owner",
                )
            if request.expected_checkpoint_digest != request_digest(cp):
                raise ProjectError(409, "Claim evidence changed; inspect the retained candidate again")
            row.settled = True
            row.checkpoint = {
                **cp,
                "lease": None,
                "lease_expires_at": None,
                "reconciliation": {
                    "request_id": str(request.request_id),
                    "actor": actor,
                    "request_digest": digest,
                    "checkpoint_digest": request.expected_checkpoint_digest,
                    "reconciled_at": get_current_utc_time().isoformat(),
                },
            }
            await session.flush()
            return claim_view(row)
