from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.features.project_management.pipeline_runs.github import github_project_error
from app.features.project_management.pipeline_runs.models import (
    ExecutionAttempt,
    ExecutionAttemptKind,
    ExecutionAttemptState,
    PipelineRun,
    PipelineRunState,
)
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.pipeline_runs.schemas import (
    ImplementationRequest,
    PipelineRunRead,
)
from app.features.project_management.pipeline_runs.usecases.transitions import (
    finish_closed_pull,
    wait_on_github,
)
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.pipelines.github import (
    GitHubActionsReader,
    GitHubObservationError,
)
from app.features.project_management.pipelines.schemas import VerificationStatus
from app.features.project_management.pipelines.services import PipelineConfigurationError, PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.models import Project
from app.features.project_management.projects.schemas import ProjectRead
from sqlalchemy.ext.asyncio import AsyncSession

# GitHub `mergeable_state` values. A branch that conflicts with or trails its base is the agent's to update;
# the others wait for a person (an approval, a branch rule, leaving draft) and are rechecked on a timer.
MERGE_NEEDS_UPDATE = ("dirty", "behind")
MERGE_WAITS_FOR_OPERATOR = ("blocked", "draft")
MERGE_RECHECK_DELAY = timedelta(minutes=5)


def _merge_wait_reason(mergeable_state: str | None) -> str:
    if mergeable_state == "draft":
        return "Waiting on GitHub: CI passed but the pull request is a draft. Mark it ready; the run merges by itself."
    if mergeable_state == "blocked":
        return (
            "Waiting on GitHub: CI passed but branch protection blocks the merge (a required review or a check "
            "Hub does not observe). Satisfy it; the run merges by itself."
        )
    return (
        "Waiting on GitHub: CI passed but GitHub refused the merge without reporting a conflict. Check the "
        "repository's allowed merge methods and branch rules; the run retries by itself."
    )


class CIProgress:
    def __init__(self, repo: PipelineRunRepository, observer: PipelineObservationService):
        self.repo = repo
        self.observer = observer

    async def advance(
        self,
        session: AsyncSession,
        run: PipelineRun,
        project: Project,
        now: datetime,
        observer: PipelineObservationService,
    ) -> PipelineRunRead:
        if project.github_connector_id is None or project.github_repository is None:
            raise ProjectError(422, "Project missing GitHub connection for pipeline run")
        project_read = ProjectRead.model_validate(project)
        if project_read.github is None:
            raise ProjectError(422, "Project missing GitHub connection for pipeline run")
        observation = await observer.observe(project_read.observation_config([run.pull_number]))
        pull_result = observation.pulls[0].result
        if pull_result.status != VerificationStatus.PASSED and run.pause_reason is not None:
            # An earlier wait (a blocked merge, say) no longer describes this head.
            run.pause_reason = None
        if pull_result.status == VerificationStatus.FAILED:
            active_attempt = await self.repo.active_attempt(session, run.id)
            # The observer exposes no failed job for a workflow-level
            # failure (for example a runner/setup outage).  That is the
            # only environment signal it can establish safely, so do
            # not ask the agent to change application code in this case.
            if not pull_result.unsuccessful_jobs:
                run.state = PipelineRunState.PAUSED
                run.pause_reason = "CI failed before a code job could be identified; inspect the environment"
                run.next_action_at = None
                run.revision += 1
                if active_attempt is not None:
                    active_attempt.state = ExecutionAttemptState.FAILED
                    active_attempt.finished_at = now
                    active_attempt.failure_code = "CI_ENVIRONMENT_FAILURE"
                    active_attempt.failure_detail = pull_result.reason
                await session.flush()
                return PipelineRunRead.model_validate(run)
            if not project_read.github.automation.auto_fix_ci:
                run.state = PipelineRunState.PAUSED
                run.pause_reason = "CI failed; automatic CI fixes are disabled for this project"
                run.next_action_at = None
                run.revision += 1
                if active_attempt is not None:
                    active_attempt.state = ExecutionAttemptState.FAILED
                    active_attempt.finished_at = now
                    active_attempt.failure_code = "CI_FAILED"
                    active_attempt.failure_detail = pull_result.reason
                await session.flush()
                return PipelineRunRead.model_validate(run)
            ci_fixes = [
                attempt
                for attempt in await self.repo.list_attempts(session, run.id)
                if attempt.kind == "ci-fix" and attempt.epoch == run.epoch
            ]
            if len(ci_fixes) >= 2:
                run.state = PipelineRunState.BLOCKED
                run.pause_reason = "CI failed after two fix requests; resume manually"
            elif active_attempt is not None:
                active_attempt.state = ExecutionAttemptState.FAILED
                active_attempt.finished_at = now
                active_attempt.failure_code = "CI_FAILED"
                active_attempt.failure_detail = pull_result.reason
                prior = ImplementationRequest.model_validate(active_attempt.request_snapshot)
                log_excerpt = await self._failed_job_log_excerpt(
                    project.github_connector_id,
                    project.github_repository,
                    observation.pulls[0].run,
                    pull_result.unsuccessful_jobs,
                )
                request = prior.model_copy(
                    update={
                        "kind": "ci-fix",
                        "correlation_marker": f"hub-attempt:{uuid4()}",
                        "pull_request": prior.pull_request.model_copy(
                            update={"head_sha": observation.pulls[0].head_sha}
                        ),
                        "instructions": prior.instructions
                        + "\n\nCI failed for this PR. Fix these jobs: "
                        + ", ".join(pull_result.unsuccessful_jobs or [pull_result.reason])
                        + (f"\n\n## Bounded failing-job log excerpt\n\n{log_excerpt}" if log_excerpt else ""),
                    }
                )
                await self.repo.create_attempt(
                    session,
                    ExecutionAttempt(
                        pipeline_run_id=run.id,
                        attempt_number=await self.repo.next_attempt_number(session, run.id),
                        epoch=run.epoch,
                        kind=ExecutionAttemptKind.CI_FIX,
                        state=ExecutionAttemptState.PLANNED,
                        request_snapshot=request.model_dump(mode="json"),
                        request_digest=request_digest(request.model_dump(mode="json")),
                        idempotency_key=UUID(request.correlation_marker.removeprefix("hub-attempt:")),
                    ),
                )
                run.state = PipelineRunState.DISPATCHING
            run.revision += 1
            await session.flush()
        elif pull_result.status == VerificationStatus.CLOSED:
            pr = await observer.get_pull_request(
                project.github_connector_id, project.github_repository, run.pull_number
            )
            if pr.get("state") == "closed":
                await finish_closed_pull(self.repo, session, run, pr, now)
        elif pull_result.status == VerificationStatus.PASSED:
            if not project_read.github.automation.auto_merge:
                run.state = PipelineRunState.PAUSED
                run.pause_reason = "CI passed; automatic merge is disabled for this project"
                run.next_action_at = None
                run.revision += 1
                active_attempt = await self.repo.active_attempt(session, run.id)
                if active_attempt is not None:
                    active_attempt.state = ExecutionAttemptState.COMPLETED
                    active_attempt.finished_at = now
                await session.flush()
                return PipelineRunRead.model_validate(run)
            # Re-observe immediately before the write; the merge API is
            # still the final authority for branch rules and head SHA.
            try:
                token_value = await self.observer.get_token(project.github_connector_id, "github")
                async with pipeline_services.create_github_client(token_value) as client:
                    reader = GitHubActionsReader(client)
                    current = await reader.observe_pull(
                        project_read.observation_config([run.pull_number]), run.pull_number
                    )
                    if current.result.status != VerificationStatus.PASSED:
                        return PipelineRunRead.model_validate(run)
                    # GitHub's own verdict decides what a refusal means: only a branch that conflicts with
                    # or trails its base is the agent's to fix. Reviews, branch rules, and drafts wait for
                    # a person, and asking the agent to "resolve conflicts" there only burns a task.
                    mergeable_state = current.mergeable_state
                    merge: dict = {"merged": False}
                    if mergeable_state not in (*MERGE_NEEDS_UPDATE, *MERGE_WAITS_FOR_OPERATOR):
                        try:
                            merge = await reader.merge_pull_request(
                                project.github_repository,
                                run.pull_number,
                                current.head_sha,
                                project_read.github.automation.merge_method,
                            )
                        except GitHubObservationError as exc:
                            if exc.status_code not in (405, 409):
                                raise
                            refused = await reader._get(f"/repos/{project.github_repository}/pulls/{run.pull_number}")
                            state = refused.get("mergeable_state")
                            mergeable_state = state if isinstance(state, str) else None
                            if mergeable_state not in MERGE_NEEDS_UPDATE:
                                mergeable_state = mergeable_state or "refused"
            except PipelineConfigurationError as exc:
                raise ProjectError(422, str(exc)) from None
            except GitHubObservationError as exc:
                raise github_project_error(exc) from None

            if merge.get("merged") is not True and mergeable_state not in MERGE_NEEDS_UPDATE:
                wait_on_github(run, _merge_wait_reason(mergeable_state), now, MERGE_RECHECK_DELAY)
                await session.flush()
                return PipelineRunRead.model_validate(run)
            if merge.get("merged") is True:
                run.state = PipelineRunState.COMPLETED
                run.pause_reason = None
                run.next_action_at = None
                run.revision += 1
                active_attempt = await self.repo.active_attempt(session, run.id)
                if active_attempt is not None:
                    active_attempt.state = ExecutionAttemptState.COMPLETED
                    active_attempt.finished_at = now
                await session.flush()
            else:
                conflicts = [
                    item
                    for item in await self.repo.list_attempts(session, run.id)
                    if item.kind == "conflict-fix" and item.epoch == run.epoch
                ]
                if not project_read.github.automation.auto_fix_conflicts:
                    run.state = PipelineRunState.PAUSED
                    run.pause_reason = "Merge failed; automatic conflict fixes are disabled for this project"
                    active_attempt = await self.repo.active_attempt(session, run.id)
                    if active_attempt is not None:
                        active_attempt.state = ExecutionAttemptState.FAILED
                        active_attempt.finished_at = now
                        active_attempt.failure_code = "MERGE_FAILED"
                        active_attempt.failure_detail = "GitHub could not merge the verified pull request"
                elif len(conflicts) >= 1:
                    run.state = PipelineRunState.BLOCKED
                    run.pause_reason = "Merge conflict persisted after one fix request; resume manually"
                else:
                    active_attempt = await self.repo.active_attempt(session, run.id)
                    if active_attempt is None:
                        raise ProjectError(409, "Pipeline run has no active attempt to revise")
                    active_attempt.state = ExecutionAttemptState.FAILED
                    active_attempt.finished_at = now
                    active_attempt.failure_code = "MERGE_CONFLICT"
                    active_attempt.failure_detail = "GitHub could not merge the verified pull request"
                    prior = ImplementationRequest.model_validate(active_attempt.request_snapshot)
                    request = prior.model_copy(
                        update={
                            "kind": "conflict-fix",
                            "correlation_marker": f"hub-attempt:{uuid4()}",
                            "pull_request": prior.pull_request.model_copy(
                                update={"head_sha": observation.pulls[0].head_sha}
                            ),
                            "instructions": prior.instructions
                            + "\n\nThe pull request cannot be merged cleanly. Merge the current base branch into this branch, resolve conflicts, run checks, and push the result.",
                        }
                    )

                    await self.repo.create_attempt(
                        session,
                        ExecutionAttempt(
                            pipeline_run_id=run.id,
                            attempt_number=await self.repo.next_attempt_number(session, run.id),
                            epoch=run.epoch,
                            kind=ExecutionAttemptKind.CONFLICT_FIX,
                            state=ExecutionAttemptState.PLANNED,
                            request_snapshot=request.model_dump(mode="json"),
                            request_digest=request_digest(request.model_dump(mode="json")),
                            idempotency_key=UUID(request.correlation_marker.removeprefix("hub-attempt:")),
                        ),
                    )
                    run.state = PipelineRunState.DISPATCHING
                    run.pause_reason = None
                run.next_action_at = None
                run.revision += 1
                await session.flush()

        return PipelineRunRead.model_validate(run)

    async def _failed_job_log_excerpt(self, connector_id: UUID, repository: str, run, failed_names: list[str]) -> str:
        """Best-effort evidence for a fix request; log access never blocks state handling."""
        if run is None:
            return ""
        failed = [job for job in run.jobs if job.name in failed_names and job.conclusion == "failure"]
        if not failed:
            return ""
        try:
            token = await self.observer.get_token(connector_id, "github")
            async with pipeline_services.create_github_client(token) as client:
                reader = GitHubActionsReader(client)
                excerpts = []
                for job in failed[:3]:
                    excerpt = await reader.job_log_excerpt(repository, job.id, max_chars=1_000)
                    if excerpt:
                        excerpts.append(f"### {job.name}\n\n```text\n{excerpt}\n```")
                return "\n\n".join(excerpts)
        except (GitHubObservationError, PipelineConfigurationError):
            return ""
