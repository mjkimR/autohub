from uuid import UUID

from app.features.project_management.pipeline_runs.models import (
    ExecutionAttempt,
    RunAnswer,
    RunQuestion,
    RunResumeReceipt,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class RunInteractionRepository:
    async def applied_decisions(self, session: AsyncSession, run_id: UUID):
        answers = (
            await session.execute(
                select(RunQuestion, RunAnswer, ExecutionAttempt.created_at)
                .join(RunAnswer, RunAnswer.question_id == RunQuestion.id)
                .join(ExecutionAttempt, ExecutionAttempt.id == RunAnswer.applied_attempt_id)
                .where(RunQuestion.pipeline_run_id == run_id, RunQuestion.state == "applied")
            )
        ).all()
        receipts = list(
            await session.scalars(select(RunResumeReceipt).where(RunResumeReceipt.pipeline_run_id == run_id))
        )
        return answers, receipts

    async def pending(self, session: AsyncSession, run_id: UUID) -> RunQuestion | None:
        return await session.scalar(
            select(RunQuestion).where(
                RunQuestion.pipeline_run_id == run_id, RunQuestion.state.in_(("open", "answered"))
            )
        )

    async def questions(self, session: AsyncSession, run_id: UUID, offset: int, limit: int):
        query = select(RunQuestion).where(RunQuestion.pipeline_run_id == run_id)
        total = await session.scalar(select(func.count()).select_from(query.subquery()))
        rows = list(
            await session.scalars(
                query.order_by(RunQuestion.created_at.desc(), RunQuestion.id).offset(offset).limit(limit)
            )
        )
        return rows, int(total or 0)

    async def answers(self, session: AsyncSession, question_id: UUID) -> list[RunAnswer]:
        return list(
            await session.scalars(
                select(RunAnswer)
                .where(RunAnswer.question_id == question_id)
                .order_by(RunAnswer.created_at, RunAnswer.id)
            )
        )
