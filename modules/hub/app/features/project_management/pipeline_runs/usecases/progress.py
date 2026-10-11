"""Observe a leased run without holding database locks during external I/O."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from app.features.ai_catalogs.services import AICatalogService
from app.features.project_management.connection_tests.guards import reject_test_ancestry, reject_test_refs
from app.features.project_management.connection_tests.models import TEST_BRANCH_PREFIX
from app.features.project_management.connection_tests.repos import ConnectionTestRepository
from app.features.project_management.pipeline_runs.adapters.base import DeliveryTarget
from app.features.project_management.pipeline_runs.models import PipelineRun, PipelineRunState
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.pipeline_runs.usecases.ci import CIProgress
from app.features.project_management.pipeline_runs.usecases.implementation import ImplementationProgress
from app.features.project_management.pipeline_runs.usecases.leases import raise_lease_conflict
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc, block_for_project_change
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.pipelines.github import GitHubActionsReader
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.models import Project
from app.features.project_management.projects.schemas import ProjectRead
from app.features.project_management.projects.services import ProjectService
from app.features.project_management.specrig.progress import SpecrigProgress, merge_ready
from app.features.project_management.work_plans.models import WorkItem, WorkPlan
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

PROGRESS_IO_SECONDS = 90
PROGRESS_LEASE_SECONDS = 120


@dataclass(frozen=True)
class AttemptVersion:
    id: UUID | None
    state: str | None = None
    delivery_id: UUID | None = None
    external_id: str | None = None
    posted_at: datetime | None = None


@dataclass(frozen=True)
class ProgressCheckpoint:
    run_id: UUID
    owner: str
    token: UUID
    revision: int
    state: PipelineRunState
    project_revision: int
    attempt: AttemptVersion


class PipelineRunProgress:
    def __init__(
        self,
        repo: PipelineRunRepository,
        projects: ProjectService,
        observer: PipelineObservationService,
        ai_catalogs: AICatalogService | None,
    ):
        self.repo = repo
        self.projects = projects
        self.observer = observer
        self.ai_catalogs = ai_catalogs

    async def _attempt_version(self, session: AsyncSession, run_id: UUID) -> AttemptVersion:
        attempt = await self.repo.active_attempt(session, run_id)
        if attempt is None:
            return AttemptVersion(None)
        delivery = await self.repo.latest_delivery(session, attempt.id)
        return AttemptVersion(
            attempt.id,
            attempt.state,
            delivery.id if delivery is not None else None,
            delivery.external_id if delivery is not None else None,
            as_utc(delivery.posted_at) if delivery is not None and delivery.posted_at is not None else None,
        )

    async def _validate(self, session: AsyncSession, checkpoint: ProgressCheckpoint) -> tuple[PipelineRun, Project]:
        # Fresh time and a fresh transaction are required: the original lease may have expired or changed hands.
        run = await self.repo.get_leased(
            session, checkpoint.run_id, owner=checkpoint.owner, token=checkpoint.token, now=get_current_utc_time()
        )
        if run is None:
            await raise_lease_conflict(self.repo, session, checkpoint.run_id, "record observation")
        if run.revision != checkpoint.revision or run.state != checkpoint.state:
            raise ProjectError(409, "Pipeline run changed during observation; retry")
        project = await self.projects.get(session, run.project_id, lock=True)
        if (
            not project.enabled
            or project.revision != checkpoint.project_revision
            or run.project_revision != project.revision
        ):
            raise ProjectError(409, "Project changed during observation; retry")
        if await self._attempt_version(session, run.id) != checkpoint.attempt:
            raise ProjectError(409, "Pipeline attempt or delivery changed during observation; retry")
        return run, project

    async def _authorize_merge(self, checkpoint: ProgressCheckpoint) -> None:
        # This short transaction closes before the GitHub write. GitHub's head SHA check is the final fence.
        async with AsyncTransaction() as session:
            run, project = await self._validate(session, checkpoint)
            if run.branch.startswith(TEST_BRANCH_PREFIX) or await ConnectionTestRepository().owns_pull(
                session, project.github_repository or "", run.pull_number
            ):
                raise ProjectError(422, "Connection test pull requests must never be merged")
            reject_test_refs(run.pull_snapshot)
            repository, connector_id, number = project.github_repository, project.github_connector_id, run.pull_number
            heads = await ConnectionTestRepository().protected_heads(session, repository or "")
            snapshot_data = getattr(run, "specrig_snapshot", None)
            native_snapshot = dict(snapshot_data) if snapshot_data else None
            progress_data = getattr(run, "specrig_progress", None)
            native_previous = dict(progress_data) if progress_data else {}
            work_binding = (
                await session.execute(
                    select(WorkPlan.base_branch, WorkItem.branch)
                    .join(WorkItem, WorkItem.plan_id == WorkPlan.id)
                    .where(WorkItem.pipeline_run_id == run.id)
                )
            ).one_or_none()
        if native_snapshot and repository and connector_id:
            pull = await self.observer.get_pull_request(connector_id, repository, number)
            approval = native_previous.get("approval")
            if (
                not approval
                or pull.get("draft")
                or pull["head"]["sha"] != (native_previous or {}).get("head_sha")
                or pull["base"]["sha"] != (native_previous or {}).get("base_sha")
                or not merge_ready(native_previous)
            ):
                raise ProjectError(409, "Native integration head, base or approval changed; re-inspect before merge")
        if (heads or work_binding) and repository and connector_id:
            token = await self.observer.get_token(connector_id, "github")
            async with pipeline_services.create_github_client(token) as client:
                reader = GitHubActionsReader(client)
                pr = await reader._get(f"/repos/{repository}/pulls/{number}")
                reject_test_refs(pr)
                if work_binding and (
                    pr.get("base", {}).get("ref") != work_binding.base_branch
                    or pr.get("head", {}).get("ref") != work_binding.branch
                ):
                    raise ProjectError(409, "Work plan PR branch changed; restore its original target before merging")
                await reject_test_ancestry(reader, repository, pr["head"]["sha"], heads)
            # An ancestry read can take time. Recheck lease and project policy after that I/O as well.
            async with AsyncTransaction() as session:
                await self._validate(session, checkpoint)

    async def advance(
        self, run_id: UUID, *, owner: str, token: UUID, observer: PipelineObservationService
    ) -> PipelineRunRead:
        implementing = ImplementationProgress(self.repo, self.ai_catalogs)
        ci = CIProgress(self.repo, self.observer)
        implementation_input = None
        project_read = None
        native_snapshot = native_previous = native_target = None
        native_result = None
        ci_result = None
        async with AsyncTransaction() as session:
            now = get_current_utc_time()
            run = await self.repo.get_leased(session, run_id, owner=owner, token=token, now=now)
            if run is None:
                await raise_lease_conflict(self.repo, session, run_id, "advance run")
            project = await self.projects.get(session, run.project_id)
            if (
                not project.enabled
                or project.revision != run.project_revision
                or project.github_repository is None
                or project.github_connector_id is None
            ):
                return await block_for_project_change(self.repo, session, run, now)
            if run.state not in (PipelineRunState.IMPLEMENTING, PipelineRunState.AWAITING_CI):
                return PipelineRunRead.model_validate(run)
            snapshot_data = getattr(run, "specrig_snapshot", None)
            if snapshot_data:
                progress_data = getattr(run, "specrig_progress", None)
                native_snapshot, native_previous = (
                    dict(snapshot_data),
                    dict(progress_data) if progress_data else {},
                )
                native_attempt = await self.repo.active_attempt(session, run.id)
                native_delivery = (
                    await self.repo.latest_delivery(session, native_attempt.id) if native_attempt else None
                )
                native_stage = native_previous.get("current", {}).get("stage") or {}
                native_previous["allow_head_change"] = bool(
                    native_attempt
                    and native_delivery
                    and native_delivery.posted_at
                    and (
                        native_attempt.kind in ("ci-fix", "conflict-fix")
                        or (
                            native_attempt.request_snapshot.get("specrig_stage") == native_stage.get("id")
                            and "lint-ci-clean" in native_stage.get("exit", [])
                        )
                    )
                )
                native_target = DeliveryTarget(project.github_connector_id, project.github_repository, run.pull_number)
            if run.state == PipelineRunState.IMPLEMENTING:
                implementation_input = await implementing.prepare(
                    session,
                    run,
                    DeliveryTarget(project.github_connector_id, project.github_repository, run.pull_number),
                )
            else:
                project_read = ProjectRead.model_validate(project)
            pull_number = run.pull_number
            checkpoint = ProgressCheckpoint(
                run.id,
                owner,
                token,
                run.revision,
                run.state,
                project.revision,
                await self._attempt_version(session, run.id),
            )
            # Bound all external reads/writes below and keep the lease longer than that budget.
            run.lease_expires_at = (
                max(as_utc(run.lease_expires_at), now + timedelta(seconds=PROGRESS_LEASE_SECONDS))
                if run.lease_expires_at
                else now + timedelta(seconds=PROGRESS_LEASE_SECONDS)
            )

        try:
            async with asyncio.timeout(PROGRESS_IO_SECONDS):
                if implementation_input is not None:
                    implementation_result = await implementing.observe(implementation_input, observer)
                if native_snapshot is not None:
                    assert native_target is not None
                    native_pull = (
                        implementation_result.pull
                        if implementation_input is not None
                        else await observer.get_pull_request(
                            native_target.connector_id, native_target.repository, pull_number
                        )
                    )
                    native_result = await SpecrigProgress(self.repo).observe(
                        native_snapshot, native_previous, native_target, native_pull, observer
                    )
                if implementation_input is None and (
                    native_result is None
                    or (
                        merge_ready(native_result.get("evidence", {}))
                        and native_result.get("evidence", {}).get("approval")
                        and native_result["evidence"]["head_sha"] == (native_previous or {}).get("head_sha")
                        and native_result["evidence"]["base_sha"] == (native_previous or {}).get("base_sha")
                    )
                ):
                    assert project_read is not None
                    ci_result = await ci.observe(
                        project_read, pull_number, observer, lambda: self._authorize_merge(checkpoint)
                    )
        except TimeoutError:
            raise ProjectError(
                504, "Pipeline observation exceeded its time budget; reconcile on the next tick"
            ) from None

        async with AsyncTransaction() as session:
            run, _ = await self._validate(session, checkpoint)
            now = get_current_utc_time()
            if implementation_input is not None:
                result = await implementing.apply(session, run, now, implementation_input, implementation_result)
                if native_result is None or run.state != PipelineRunState.IMPLEMENTING:
                    return result
            if native_result is not None and ci_result is None:
                return await SpecrigProgress(self.repo).apply(session, run, now, native_result)
            assert project_read is not None and ci_result is not None
            if native_result is not None:
                run.specrig_progress = native_result["evidence"]
            return await ci.apply(session, run, project_read, now, ci_result)
