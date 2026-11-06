"""Shared durable native-start reservation for single and batch entry points."""

from datetime import datetime, timedelta
from uuid import uuid4

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time

from .batch_models import SddActivityClaim
from .batch_policy import project_basis, same_request
from .batch_repo import BatchRepository


class ActivityClaims:
    def __init__(self, projects, observer, runs):
        self.projects, self.observer, self.runs, self.repo = projects, observer, runs, BatchRepository()

    async def reserve(self, session, project, activity, slug, request, actor, *, member_id=None, expected_sha=None):
        digest = request_digest(request.model_dump(mode="json"))
        existing = await self.repo.claim_request(session, project.id, request.request_id)
        if existing:
            same_request(existing, actor, digest)
            if (
                existing.member_id != member_id
                or existing.unit != f"docs/proposals/PROP-{slug}"
                or existing.activity != activity
            ):
                raise ProjectError(409, "Start request belongs to another activity owner")
            return existing
        unit = f"docs/proposals/PROP-{slug}"
        if await self.repo.claim_active(session, project.id, unit, activity):
            raise ProjectError(409, "This native activity has a different unsettled owner")
        return await self.repo.save(
            session,
            SddActivityClaim(
                project_id=project.id,
                member_id=member_id,
                request_id=request.request_id,
                actor=actor,
                request_digest=digest,
                unit=unit,
                activity=activity,
                checkpoint={
                    "project": project_basis(project),
                    "expected_sha": expected_sha,
                    "request": request.model_dump(mode="json"),
                },
            ),
        )

    async def execute(self, project_id, claim_id):
        from .activities import ActivityStarter
        from .batch_models import SddActivityClaim
        from .schemas import StartActivityRequest

        lease = str(uuid4())
        async with AsyncTransaction() as session:
            project = await self.projects.get(session, project_id, lock=True)
            claim = await session.get(SddActivityClaim, claim_id, with_for_update=True)
            if claim is None or claim.project_id != project_id:
                raise ProjectError(404, "Native activity claim not found")
            if claim.run_id:
                return await self.runs.get(claim.run_id)
            cp = dict(claim.checkpoint)
            expires = cp.get("lease_expires_at")
            if expires and datetime.fromisoformat(expires) > get_current_utc_time():
                raise ProjectError(409, "Native activity reconciliation is already in flight")
            if project_basis(project) != cp["project"]:
                raise ProjectError(409, "Project changed after native admission claim")
            cp.update(lease=lease, lease_expires_at=(get_current_utc_time() + timedelta(minutes=5)).isoformat())
            claim.checkpoint = cp
            request, activity, actor = StartActivityRequest(**cp["request"]), claim.activity, claim.actor
            unit = claim.unit

        async def checkpoint(**values):
            async with AsyncTransaction() as session:
                current = await self.projects.get(session, project_id, lock=True)
                row = await session.get(SddActivityClaim, claim_id, with_for_update=True)
                if row is None or row.checkpoint.get("lease") != lease or project_basis(current) != cp["project"]:
                    raise ProjectError(409, "Native activity claim fence changed")
                row.checkpoint = {**row.checkpoint, **values}
                cp.update(values)

        try:
            result = await ActivityStarter(self.observer, self.runs).start(
                project,
                activity,
                unit.rsplit("PROP-", 1)[1],
                request,
                actor,
                expected_base_sha=cp.get("expected_sha"),
                checkpoint=checkpoint,
                saved=cp,
            )
            async with AsyncTransaction() as session:
                await self.projects.get(session, project_id, lock=True)
                row = await session.get(SddActivityClaim, claim_id, with_for_update=True)
                if row is None or row.checkpoint.get("lease") != lease:
                    raise ProjectError(409, "Native enrollment result requires reconciliation")
                row.run_id = result.id
                row.checkpoint = {**row.checkpoint, "lease_expires_at": None, "run_id": str(result.id)}
            return result
        except BaseException:
            # Preserve every remote checkpoint; another invocation reconciles the same claim.
            async with AsyncTransaction() as session:
                row = await session.get(SddActivityClaim, claim_id, with_for_update=True)
                if row is not None and row.checkpoint.get("lease") == lease:
                    row.checkpoint = {**row.checkpoint, "lease_expires_at": None, "uncertain": True}
            raise
