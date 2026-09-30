"""Decision records share the run lock with pause, resume and result observation."""

from uuid import UUID

from app.features.project_management.pipeline_runs.interaction_repo import RunInteractionRepository
from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES, PipelineRun, RunAnswer, RunQuestion
from app.features.project_management.projects.errors import ProjectError
from sqlalchemy.ext.asyncio import AsyncSession


def check_revision(run: PipelineRun, expected: int) -> None:
    if run.revision != expected:
        raise ProjectError(409, "Run changed; reload before applying this decision")
    if run.state in FINAL_RUN_STATES:
        raise ProjectError(409, "The run has ended; register replacement work instead")


class RunInteractionService:
    def __init__(self):
        self.repo = RunInteractionRepository()

    async def ask(
        self,
        session: AsyncSession,
        run: PipelineRun,
        *,
        request_id: UUID,
        question: str,
        actor: str,
        source: str,
        head_sha: str,
        attempt_id: UUID | None,
        invalidate_lease: bool = True,
    ) -> RunQuestion:
        existing = await session.get(RunQuestion, request_id)
        if existing is not None:
            if (existing.pipeline_run_id, existing.question, existing.actor, existing.head_sha) != (
                run.id,
                question,
                actor,
                head_sha,
            ):
                raise ProjectError(409, "Question request ID was already used for different content")
            return existing
        if await self.repo.pending(session, run.id):
            raise ProjectError(409, "Answer or dismiss the existing question first")
        row = RunQuestion(
            id=request_id,
            pipeline_run_id=run.id,
            execution_attempt_id=attempt_id,
            head_sha=head_sha,
            question=question,
            actor=actor,
            source=source,
        )
        session.add(row)
        run.state = "blocked"
        run.pause_reason = "Operator decision required: " + question[:500]
        run.next_action_at = None
        if invalidate_lease:
            run.lease_owner = run.lease_token = run.lease_expires_at = None
        run.revision += 1
        await session.flush()
        return row

    async def response_for_resume(
        self, session: AsyncSession, run: PipelineRun, answer_id: UUID | None
    ) -> tuple[RunQuestion, RunAnswer] | None:
        pending = await self.repo.pending(session, run.id)
        if answer_id is None:
            if pending:
                raise ProjectError(409, "Select a saved answer or dismiss the pending question before resuming")
            return None
        answer = await session.get(RunAnswer, answer_id)
        if (
            pending is None
            or answer is None
            or answer.question_id != pending.id
            or answer.applied_attempt_id is not None
        ):
            raise ProjectError(409, "Answer does not belong to the current pending question")
        return pending, answer
