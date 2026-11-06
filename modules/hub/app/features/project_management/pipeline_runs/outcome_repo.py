"""Exact request lookup within the selected owner's namespace."""

from sqlalchemy import select

from .models import ExecutionAttempt, ExecutionDelivery, RunAnswer, RunQuestion, RunResumeReceipt


class DecisionOutcomeRepository:
    async def record(self, session, run_id, request_id, operation):
        model = {"question": RunQuestion, "answer": RunAnswer, "resume": RunResumeReceipt}[operation]
        row = await session.get(model, request_id)
        if row is None:
            return None, None
        question = await session.get(RunQuestion, row.question_id) if operation == "answer" else None
        owner = question if operation == "answer" else row
        if owner is None or owner.pipeline_run_id != run_id:
            return None, None
        return row, question

    async def attempt(self, session, run_id, attempt_id):
        row = await session.get(ExecutionAttempt, attempt_id) if attempt_id else None
        if row is None or row.pipeline_run_id != run_id:
            return None, None
        delivery = await session.scalar(
            select(ExecutionDelivery)
            .where(ExecutionDelivery.execution_attempt_id == row.id)
            .order_by(ExecutionDelivery.delivery_number.desc())
            .limit(1)
        )
        return row, delivery
