"""Durable optimistic activity publication and permanent legacy-owner fencing."""

from datetime import datetime, timedelta
from uuid import uuid4

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time

from .batch_models import SddActivityClaim
from .batch_policy import project_basis, same_request
from .batch_repo import BatchRepository
from .execution import EXECUTION_VERSION, RETIRED_CODE, RETIRED_REASON


class ActivityClaims:
    def __init__(self, projects, observer, runs):
        self.projects, self.observer, self.runs, self.repo = projects, observer, runs, BatchRepository()

    async def reserve(self, session, project, activity, slug, request, actor, *, member_id=None, expected_sha=None):
        digest = request_digest(request.model_dump(mode="json"))
        existing = await self.repo.claim_request(session, project.id, request.request_id)
        if existing:
            if existing.checkpoint.get("execution_version") != EXECUTION_VERSION or existing.checkpoint.get("retired"):
                raise ProjectError(
                    410,
                    f"{RETIRED_REASON}; inspect /api/v1/projects/{project.id}/sdd/claims/{existing.id}",
                    code=RETIRED_CODE,
                )
            same_request(existing, actor, digest)
            if (
                existing.member_id != member_id
                or existing.unit != f"docs/proposals/PROP-{slug}"
                or existing.activity != activity
            ):
                raise ProjectError(409, "Start request belongs to another activity owner")
            return existing
        unit = f"docs/proposals/PROP-{slug}"
        owner = await self.repo.claim_active(session, project.id, unit, activity)
        if owner:
            raise ProjectError(
                409,
                f"Activity has unsettled owner claim {owner.id}; inspect /api/v1/projects/{project.id}/sdd/claims/{owner.id}",
                code="SDD_ACTIVITY_OWNED",
            )
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
                    "execution_version": EXECUTION_VERSION,
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

        owner_reference = f"/api/v1/projects/{project_id}/sdd/claims/{claim_id}"
        lease = str(uuid4())
        async with AsyncTransaction() as session:
            project = await self.projects.get(session, project_id, lock=True)
            claim = await session.get(SddActivityClaim, claim_id, with_for_update=True)
            if claim is None or claim.project_id != project_id:
                raise ProjectError(404, "Native activity claim not found")
            if claim.checkpoint.get("execution_version") != EXECUTION_VERSION or claim.checkpoint.get("retired"):
                raise ProjectError(
                    410,
                    f"{RETIRED_REASON}; inspect /api/v1/projects/{project_id}/sdd/claims/{claim.id}",
                    code=RETIRED_CODE,
                )
            if claim.run_id:
                claim.checkpoint = {**claim.checkpoint, "uncertain": False}
                return await self.runs.get(claim.run_id)
            cp = dict(claim.checkpoint)
            if cp.get("refusal"):
                raise ProjectError(
                    cp["refusal"]["status"],
                    f"{cp['refusal']['detail']}; inspect {owner_reference}",
                    code=cp["refusal"].get("code"),
                )
            if claim.settled:
                raise ProjectError(
                    409,
                    f"Activity already settled; inspect {owner_reference}. Replay creates no new activity",
                )
            expires = cp.get("lease_expires_at")
            if expires and datetime.fromisoformat(expires) > get_current_utc_time():
                raise ProjectError(409, f"Activity reconciliation is already in flight; inspect {owner_reference}")
            if project_basis(project) != cp["project"]:
                raise ProjectError(409, f"Project changed after activity claim; inspect {owner_reference}")
            cp.update(lease=lease, lease_expires_at=(get_current_utc_time() + timedelta(minutes=5)).isoformat())
            claim.checkpoint = cp
            request, activity, actor = StartActivityRequest(**cp["request"]), claim.activity, claim.actor
            unit = claim.unit

        async def checkpoint(**values):
            async with AsyncTransaction() as session:
                current = await self.projects.get(session, project_id, lock=True)
                row = await session.get(SddActivityClaim, claim_id, with_for_update=True)
                if (
                    row is None
                    or row.checkpoint.get("lease") != lease
                    or project_basis(current) != cp["project"]
                    or not lease_valid(row.checkpoint)
                ):
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
                admission=(claim_id, lease),
            )
            async with AsyncTransaction() as session:
                await self.projects.get(session, project_id, lock=True)
                row = await session.get(SddActivityClaim, claim_id, with_for_update=True)
                if row is None or row.checkpoint.get("lease") != lease or not lease_valid(row.checkpoint):
                    raise ProjectError(409, "Native enrollment result requires reconciliation")
                row.run_id = result.id
                row.checkpoint = {
                    **row.checkpoint,
                    "lease_expires_at": None,
                    "run_id": str(result.id),
                    "uncertain": False,
                }
            return result
        except BaseException as exc:
            # Preserve every remote checkpoint; another invocation reconciles the same claim.
            async with AsyncTransaction() as session:
                row = await session.get(SddActivityClaim, claim_id, with_for_update=True)
                if row is not None and row.checkpoint.get("lease") == lease and lease_valid(row.checkpoint):
                    no_effect = not row.checkpoint.get("ref_attempted") and not row.checkpoint.get("pull_number")
                    refusal = {
                        "status": exc.status if isinstance(exc, ProjectError) else 503,
                        "code": exc.code if isinstance(exc, ProjectError) else None,
                        "detail": exc.detail
                        if isinstance(exc, ProjectError)
                        else "Activity start failed before branch or PR publication",
                    }
                    row.checkpoint = {
                        **row.checkpoint,
                        "lease_expires_at": None,
                        "uncertain": not no_effect,
                        "uncertainty_observed_at": get_current_utc_time().isoformat(),
                        "last_error": exc.detail
                        if isinstance(exc, ProjectError)
                        else "Activity publication was uncertain after retained artifacts (" + type(exc).__name__ + ")",
                        **({"refusal": refusal} if no_effect else {}),
                    }
                    if no_effect:
                        row.settled = True
            if isinstance(exc, ProjectError):
                raise ProjectError(exc.status, f"{exc.detail}; inspect {owner_reference}", code=exc.code) from exc
            raise


def lease_valid(checkpoint):
    expires = checkpoint.get("lease_expires_at")
    return isinstance(expires, str) and datetime.fromisoformat(expires) > get_current_utc_time()


async def settle_individual_claims(projects, *, limit=20):
    """Retain exact final owner tombstones before releasing standalone reservations."""
    from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES, PipelineRun
    from sqlalchemy import select

    async with AsyncTransaction() as session:
        ids = list(
            await session.execute(
                select(SddActivityClaim.project_id, SddActivityClaim.id)
                .join(PipelineRun, PipelineRun.id == SddActivityClaim.run_id)
                .where(
                    SddActivityClaim.member_id.is_(None),
                    SddActivityClaim.checkpoint["execution_version"].as_integer() == EXECUTION_VERSION,
                    ~SddActivityClaim.settled,
                    PipelineRun.state.in_(FINAL_RUN_STATES),
                )
                .order_by(SddActivityClaim.id)
                .limit(limit)
            )
        )
    for project_id, claim_id in ids:
        async with AsyncTransaction() as session:
            await projects.get(session, project_id, lock=True)
            row = await session.get(SddActivityClaim, claim_id, with_for_update=True)
            if row is None or row.settled or row.run_id is None:
                continue
            run = await session.get(PipelineRun, row.run_id)
            if run is None or run.state not in FINAL_RUN_STATES or run.project_id != project_id:
                continue
            row.checkpoint = {
                **row.checkpoint,
                "outcome": {
                    "state": run.state,
                    "run_id": str(run.id),
                    "pull_number": run.pull_number,
                    "pull_url": run.pull_url,
                },
            }
            row.settled = True


async def bind_enrollment(session, project, run, admission):
    """Bind the reserved owner in enrollment's transaction, before a response can be lost."""
    from app.features.project_management.branches import activity_branch

    claim_id, lease = admission
    row = await session.get(SddActivityClaim, claim_id, with_for_update=True)
    if (
        row is None
        or row.project_id != project.id
        or row.run_id is not None
        or row.checkpoint.get("execution_version") != EXECUTION_VERSION
        or row.checkpoint.get("retired")
        or row.settled
        or row.checkpoint.get("lease") != lease
        or not lease_valid(row.checkpoint)
        or row.checkpoint.get("project") != project_basis(project)
    ):
        raise ProjectError(409, "Native enrollment admission owner changed")
    cp = row.checkpoint
    enrollment = cp.get("enrollment_request") or {}
    snapshot = run.sdd_snapshot or {}
    if (
        snapshot.get("execution_version") != EXECUTION_VERSION
        or snapshot.get("provider") != "repository-agent"
        or enrollment.get("pull_number") != run.pull_number
        or enrollment.get("spec_dir") != row.unit
        or enrollment.get("activity_effort") != snapshot.get("activity_effort")
        or snapshot.get("spec_dir") != row.unit
        or bool(snapshot.get("handoff_pending")) != (row.activity == "dev")
        or run.branch != activity_branch(row.activity, row.unit.rsplit("PROP-", 1)[1])
        or cp.get("branch") != run.branch
        or cp.get("pull_number") != run.pull_number
        or cp.get("initial_sha") != (run.pull_snapshot or {}).get("head_sha")
        or run.github_repository != cp["project"]["repository"]
        or str(run.github_connector_id) != cp["project"]["connector_id"]
    ):
        raise ProjectError(409, "Native enrollment does not match the reserved exact artifacts")
    row.run_id = run.id
    row.checkpoint = {**cp, "run_id": str(run.id)}
