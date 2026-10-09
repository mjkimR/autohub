from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from app.features.project_management.pipeline_runs.interaction_schemas import ResumeRunRequest
from app.features.project_management.pipeline_runs.interaction_service import RunInteractionService
from app.features.project_management.pipeline_runs.models import (
    FINAL_RUN_STATES,
    ExecutionAttempt,
    ExecutionAttemptKind,
    ExecutionAttemptState,
    ExecutionDelivery,
    PipelineRunState,
    RunResumeReceipt,
)
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.requests import build_implementation_request, request_digest
from app.features.project_management.pipeline_runs.schemas import (
    AttachPRRequest,
    CompleteAttemptRequest,
    ExecutionAttemptRead,
    ImplementationRequest,
    PauseRunRequest,
    PipelineRunRead,
)
from app.features.project_management.pipeline_runs.usecases.catalogs import run_catalog
from app.features.project_management.pipeline_runs.usecases.delivery import DISPATCH_IO_SECONDS
from app.features.project_management.pipeline_runs.usecases.transitions import (
    EXTERNAL_IMPLEMENTATION_STATUS,
    GITHUB_BINDING_CHANGED_CONFLICT,
    finish_closed_pull,
)
from app.features.project_management.pipelines.github import (
    GitHubObservationError,
)
from app.features.project_management.pipelines.services import PipelineConfigurationError, PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time


class PipelineRunControl:
    def __init__(self, repo: PipelineRunRepository, projects: ProjectService, observer: PipelineObservationService):
        self.repo = repo
        self.projects = projects
        self.observer = observer

    async def pause_run(self, run_id: UUID, request: PauseRunRequest | None = None) -> PipelineRunRead:
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            if run is None:
                raise ProjectError(404, "Pipeline run not found")
            if run.state in (PipelineRunState.COMPLETED, PipelineRunState.FAILED, PipelineRunState.CANCELED):
                raise ProjectError(422, f"Cannot pause a run in {run.state} state")
            run.state = PipelineRunState.PAUSED
            run.pause_reason = request.reason if request and request.reason else "Manually paused by user"
            run.lease_owner = None
            run.lease_token = None
            run.lease_expires_at = None
            run.revision += 1
            await session.flush()
            return PipelineRunRead.model_validate(run)

    async def resume_run(
        self,
        run_id: UUID,
        *,
        expected_revision: int | None = None,
        request: ResumeRunRequest | None = None,
        actor: str = "operator",
        expected_head_sha: str | None = None,
        guard=None,
    ) -> PipelineRunRead:
        interactions = RunInteractionService()
        digest = (
            request_digest({"run_id": str(run_id), "actor": actor, "request": request.model_dump(mode="json")})
            if request
            else None
        )
        if request:
            expected_revision = request.expected_revision

        async def replay(session, run):
            receipt = await session.get(RunResumeReceipt, request.request_id) if request else None
            if receipt:
                if receipt.pipeline_run_id != run_id or receipt.request_digest != digest:
                    raise ProjectError(409, "Resume request ID was already used for different input")
                return PipelineRunRead.model_validate(run)
            return None

        async def remember(session, attempt_id=None):
            if request:
                session.add(
                    RunResumeReceipt(
                        id=request.request_id,
                        pipeline_run_id=run_id,
                        request_digest=digest,
                        execution_attempt_id=attempt_id,
                    )
                )
                await session.flush()

        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            if run is None:
                raise ProjectError(404, "Pipeline run not found")
            if guard is not None:
                await guard(session, run)
            if result := await replay(session, run):
                return result
            if expected_revision is not None and run.revision != expected_revision:
                raise ProjectError(
                    409,
                    "Run changed since inspection",
                    fix="Read the run and inspect its state and pause reason before resuming with the current revision.",
                )
            if run.state not in (PipelineRunState.PAUSED, PipelineRunState.BLOCKED):
                raise ProjectError(
                    422, f"Cannot resume a run that is not paused or blocked (current state: {run.state})"
                )
            await interactions.response_for_resume(session, run, request.answer_id if request else None)
            attempts = await self.repo.list_attempts(session, run.id)
            expected_revision = run.revision
            project = await self.projects.get(session, run.project_id)
            if not project.enabled:
                raise ProjectError(409, "Project is disabled; enable it before resuming")
            if project.github_connector_id is None or project.github_repository is None:
                raise ProjectError(422, "Project missing GitHub connection for pipeline run")
            if project.revision != run.project_revision and (
                run.github_repository != project.github_repository
                or run.github_connector_id != project.github_connector_id
            ):
                # Another repository can resolve the same PR number to a different pull request, and another account
                # can neither reconcile earlier mentions nor share this catalog's quota.
                raise ProjectError(409, GITHUB_BINDING_CHANGED_CONFLICT)
            project_revision = project.revision
            connector_id, repository, pull_number = (
                project.github_connector_id,
                project.github_repository,
                run.pull_number,
            )
            # A pull request implemented outside the pipeline has nothing to re-send: its resume goes back to
            # watching CI. Only attempts the pipeline itself delivered are replayed.
            external = attempts[-1].external_status == EXTERNAL_IMPLEMENTATION_STATUS if attempts else False
            if attempts:
                previous = attempts[-1]
                prior = ImplementationRequest.model_validate(previous.request_snapshot)
                kind = previous.kind
            else:
                prior, _, _ = build_implementation_request(run, repository)
                kind = ExecutionAttemptKind.IMPLEMENTATION

        try:
            async with asyncio.timeout(DISPATCH_IO_SECONDS):
                pr = await self.observer.get_pull_request(connector_id, repository, pull_number)
            if pr.get("state") not in ("open", "closed"):
                raise ValueError("Missing pull request state")
            pull = prior.pull_request.model_copy(
                update={"head_sha": pr["head"]["sha"], "head_ref": pr["head"]["ref"], "base_ref": pr["base"]["ref"]}
            )
            if expected_head_sha is not None and pull.head_sha != expected_head_sha:
                raise ProjectError(409, "PR head changed since flow approval")
            if not pull.head_sha or not pull.head_ref or not pull.base_ref:
                raise ValueError("Missing pull request revision")
        except TimeoutError:
            raise ProjectError(504, "Pull request read exceeded its time budget") from None
        except (GitHubObservationError, PipelineConfigurationError):
            raise ProjectError(502, "Could not read the pull request before resuming") from None
        except (KeyError, TypeError, ValueError):
            raise ProjectError(502, "GitHub returned incomplete pull request data") from None

        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            if guard is not None and run is not None:
                await guard(session, run)
            if run is not None and (result := await replay(session, run)):
                return result
            if run is None or run.revision != expected_revision:
                raise ProjectError(409, "Pipeline run changed while resuming; reload and retry")
            project = await self.projects.get(session, run.project_id)
            if not project.enabled or project.revision != project_revision:
                raise ProjectError(409, "Project changed while resuming; reload and retry")
            response = await interactions.response_for_resume(session, run, request.answer_id if request else None)
            now = get_current_utc_time()
            if pr["state"] == "closed":
                await finish_closed_pull(self.repo, session, run, pr, now)
                await remember(session)
                return PipelineRunRead.model_validate(run)
            if pull.head_ref != run.branch:
                raise ProjectError(409, "Pull request branch changed; enroll it again")
            if response is not None and response[0].head_sha != pull.head_sha:
                raise ProjectError(
                    409, "PR head changed since the question; inspect and dismiss the stale question before resuming"
                )
            active = await self.repo.active_attempt(session, run.id)
            delivery = await self.repo.latest_delivery(session, active.id) if active is not None else None
            # The agent pushed after the last delivered request, e.g. while the run was paused. Sending it again
            # would only produce a reply without a push, so watch CI for that push. An answer still sends new work.
            pushed = (
                active is not None
                and delivery is not None
                and delivery.posted_at is not None
                and ImplementationRequest.model_validate(active.request_snapshot).pull_request.head_sha != pull.head_sha
            )
            if (external or pushed) and response is None:
                run.state = PipelineRunState.AWAITING_CI
                run.next_action_at = None
                run.pause_reason = None
                run.project_revision = project_revision
                run.ai_catalog_id = (await run_catalog(session, project, run)).id
                run.revision += 1
                await remember(session)
                await session.flush()
                return PipelineRunRead.model_validate(run)
            if active is not None:
                active.state = ExecutionAttemptState.FAILED
                active.finished_at = now
                active.failure_code = "USER_RESUMED"
                active.failure_detail = "Superseded by a user-initiated resume"
            run.epoch += 1
            key = uuid4()
            implementation = prior.model_copy(update={"correlation_marker": f"hub-attempt:{key}", "pull_request": pull})
            if response is not None:
                question, answer = response
                implementation = implementation.model_copy(
                    update={
                        "instructions": prior.instructions
                        + f"\n\nOperator decision ({question.id}):\nQuestion: {question.question}\nAnswer: {answer.answer}\n"
                        "Apply this clarification within the original scope. If it changes acceptance criteria, stop and ask again."
                    }
                )
            snapshot = implementation.model_dump(mode="json")
            attempt = await self.repo.create_attempt(
                session,
                ExecutionAttempt(
                    pipeline_run_id=run.id,
                    attempt_number=await self.repo.next_attempt_number(session, run.id),
                    epoch=run.epoch,
                    kind=kind,
                    state=ExecutionAttemptState.PLANNED,
                    request_snapshot=snapshot,
                    request_digest=request_digest(snapshot),
                    idempotency_key=key,
                ),
            )
            await self.repo.create_delivery(
                session, ExecutionDelivery(execution_attempt_id=attempt.id, delivery_number=1, cause="resume")
            )
            if response is not None:
                response[0].state = "applied"
                response[1].applied_attempt_id = attempt.id
            await remember(session, attempt.id)
            run.state = PipelineRunState.DISPATCHING
            run.next_action_at = None
            run.pause_reason = None
            # The operator's resume accepts settings changes; later ticks follow the current project.
            run.project_revision = project_revision
            # The new attempt keeps a catalog designated at enrollment, else follows the project's current selection.
            run.ai_catalog_id = (await run_catalog(session, project, run)).id
            run.revision += 1
            await session.flush()
            return PipelineRunRead.model_validate(run)

    async def cancel_run(self, run_id: UUID) -> PipelineRunRead:
        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            if run is None:
                raise ProjectError(404, "Pipeline run not found")
            if run.state in (PipelineRunState.COMPLETED, PipelineRunState.FAILED, PipelineRunState.CANCELED):
                raise ProjectError(422, f"Cannot cancel a run in {run.state} state")
            run.state = PipelineRunState.CANCELED
            run.pause_reason = "Manually canceled"
            run.lease_owner = None
            run.lease_token = None
            run.lease_expires_at = None
            run.revision += 1
            active_attempt = await self.repo.active_attempt(session, run.id)
            if active_attempt is not None:
                active_attempt.state = ExecutionAttemptState.FAILED
                active_attempt.failure_code = "CANCELED"
                active_attempt.failure_detail = "Run was canceled"
                active_attempt.finished_at = now
            await session.flush()
            return PipelineRunRead.model_validate(run)

    async def attach_pr(self, run_id: UUID, request: AttachPRRequest) -> PipelineRunRead:
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            if run is None:
                raise ProjectError(404, "Pipeline run not found")
            if run.state not in (PipelineRunState.QUEUED, PipelineRunState.DISPATCHING, PipelineRunState.IMPLEMENTING):
                raise ProjectError(422, f"Cannot attach PR to a run in {run.state} state")
            project = await self.projects.get(session, run.project_id)
            repo_name = project.github_repository or "repo"
            run.pull_number = request.pull_number
            run.pull_url = request.pull_url or f"https://github.com/{repo_name}/pull/{request.pull_number}"
            run.state = PipelineRunState.AWAITING_CI
            run.revision += 1
            active_attempt = await self.repo.active_attempt(session, run.id)
            if active_attempt is not None and active_attempt.state in (
                ExecutionAttemptState.PLANNED,
                ExecutionAttemptState.DISPATCHING,
            ):
                active_attempt.state = ExecutionAttemptState.RUNNING
            await session.flush()
            return PipelineRunRead.model_validate(run)

    async def complete_attempt(
        self, run_id: UUID, attempt_id: UUID, request: CompleteAttemptRequest
    ) -> ExecutionAttemptRead:
        """Record what an external worker reports for its attempt.

        Only an attempt that is still open on a run that is still active can be reported on: a settled attempt or
        a finished run is history, and a late or repeated report must not rewrite it or fail the run again.
        """
        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            if run is None:
                raise ProjectError(404, "Pipeline run not found")
            attempt = await self.repo.get_attempt(session, attempt_id)
            if attempt is None or attempt.pipeline_run_id != run_id:
                raise ProjectError(404, "Execution attempt not found for this pipeline run")
            if run.state in FINAL_RUN_STATES:
                raise ProjectError(409, f"Pipeline run is already {run.state}")
            if attempt.state in (ExecutionAttemptState.COMPLETED, ExecutionAttemptState.FAILED):
                raise ProjectError(409, f"Execution attempt is already {attempt.state}")
            if request.status == "completed":
                attempt.state = ExecutionAttemptState.COMPLETED
                attempt.finished_at = now
            else:
                attempt.state = ExecutionAttemptState.FAILED
                attempt.finished_at = now
                attempt.failure_code = request.failure_code or "WORKER_FAILED"
                attempt.failure_detail = request.failure_detail or "External worker reported failure"
                if run.state in (PipelineRunState.DISPATCHING, PipelineRunState.IMPLEMENTING):
                    run.state = PipelineRunState.FAILED
                    run.pause_reason = attempt.failure_detail
                    run.revision += 1
            await session.flush()
            return ExecutionAttemptRead.model_validate(attempt)
