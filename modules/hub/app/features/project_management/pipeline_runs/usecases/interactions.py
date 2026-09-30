import asyncio
from typing import Annotated
from uuid import UUID

from app.features.project_management.pipeline_runs.interaction_schemas import (
    AnswerRead,
    AnswerWrite,
    QuestionDismiss,
    QuestionList,
    QuestionRead,
    QuestionWrite,
)
from app.features.project_management.pipeline_runs.interaction_service import RunInteractionService, check_revision
from app.features.project_management.pipeline_runs.models import RunAnswer, RunQuestion
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.pipelines.github import GitHubObservationError
from app.features.project_management.pipelines.services import PipelineConfigurationError
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends


class RunInteractionUseCase:
    def __init__(self, lifecycle: Annotated[PipelineRunUseCase, Depends()]):
        self.lifecycle = lifecycle
        self.runs = PipelineRunRepository()
        self.service = RunInteractionService()

    async def _run(self, session, run_id):
        run = await self.runs.get(session, run_id, lock=True)
        if run is None:
            raise ProjectError(404, "Run not found")
        return run

    async def _read(self, session, row):
        return QuestionRead.model_validate(row).model_copy(
            update={"answers": [AnswerRead.model_validate(a) for a in await self.service.repo.answers(session, row.id)]}
        )

    async def list(self, run_id: UUID, offset: int = 0, limit: int = 50) -> QuestionList:
        async with AsyncTransaction() as session:
            run = await self._run(session, run_id)
            rows, total = await self.service.repo.questions(session, run_id, offset, limit)
            return QuestionList(
                items=[await self._read(session, row) for row in rows], total_count=total, run_revision=run.revision
            )

    async def ask(self, run_id: UUID, data: QuestionWrite, actor: str) -> QuestionRead:
        async with AsyncTransaction() as session:
            run = await self._run(session, run_id)
            existing = await session.get(RunQuestion, data.request_id)
            if existing:
                if (existing.pipeline_run_id, existing.question, existing.actor) != (run_id, data.question, actor):
                    raise ProjectError(409, "Question request ID conflict")
                return await self._read(session, existing)
            check_revision(run, data.expected_revision)
            project = await self.lifecycle.projects.get(session, run.project_id)
            connector, repository = project.github_connector_id, project.github_repository
            if (
                connector is None
                or repository is None
                or (run.github_repository and run.github_repository != repository)
                or (run.github_connector_id and run.github_connector_id != connector)
            ):
                raise ProjectError(409, "Restore the run's GitHub connection before asking a question")
            project_revision, number = project.revision, run.pull_number
        try:
            async with asyncio.timeout(30):
                pull = await self.lifecycle.observer.get_pull_request(connector, repository, number)
        except TimeoutError:
            raise ProjectError(504, "Pull request read exceeded its time budget") from None
        except (GitHubObservationError, PipelineConfigurationError):
            raise ProjectError(502, "Could not read the pull request before recording a question") from None
        async with AsyncTransaction() as session:
            run = await self._run(session, run_id)
            existing = await session.get(RunQuestion, data.request_id)
            if existing:
                if (existing.pipeline_run_id, existing.question, existing.actor) != (run_id, data.question, actor):
                    raise ProjectError(409, "Question request ID conflict")
                return await self._read(session, existing)
            check_revision(run, data.expected_revision)
            project = await self.lifecycle.projects.get(session, run.project_id)
            if (
                project.revision != project_revision
                or pull.get("state") != "open"
                or pull.get("head", {}).get("ref") != run.branch
            ):
                raise ProjectError(409, "Project or pull request changed; reload before asking")
            head = pull.get("head", {}).get("sha")
            if not isinstance(head, str) or not head:
                raise ProjectError(502, "GitHub returned no pull request head")
            attempts = await self.runs.list_attempts(session, run_id)
            row = await self.service.ask(
                session,
                run,
                request_id=data.request_id,
                question=data.question,
                actor=actor,
                source="operator",
                head_sha=head,
                attempt_id=attempts[-1].id if attempts else None,
            )
            return await self._read(session, row)

    async def answer(self, run_id: UUID, question_id: UUID, data: AnswerWrite, actor: str) -> AnswerRead:
        async with AsyncTransaction() as session:
            run = await self._run(session, run_id)
            existing = await session.get(RunAnswer, data.request_id)
            if existing:
                owner = await session.get(RunQuestion, existing.question_id)
                if (
                    (existing.question_id, existing.answer, existing.actor) != (question_id, data.answer, actor)
                    or owner is None
                    or owner.pipeline_run_id != run_id
                ):
                    raise ProjectError(409, "Answer request ID conflict")
                return AnswerRead.model_validate(existing)
            check_revision(run, data.expected_revision)
            pending = await self.service.repo.pending(session, run_id)
            if pending is None or pending.id != question_id:
                raise ProjectError(409, "Question is no longer pending")
            row = RunAnswer(id=data.request_id, question_id=question_id, answer=data.answer, actor=actor)
            session.add(row)
            pending.state = "answered"
            run.revision += 1
            await session.flush()
            return AnswerRead.model_validate(row)

    async def dismiss(self, run_id: UUID, question_id: UUID, data: QuestionDismiss, actor: str) -> QuestionRead:
        async with AsyncTransaction() as session:
            run = await self._run(session, run_id)
            check_revision(run, data.expected_revision)
            question = await self.service.repo.pending(session, run_id)
            if question is None or question.id != question_id:
                raise ProjectError(409, "Question is no longer pending")
            question.state = "dismissed"
            question.resolution = f"{actor}: {data.reason}"
            run.pause_reason = "Question dismissed; inspect the PR before resuming"
            run.revision += 1
            await session.flush()
            return await self._read(session, question)
