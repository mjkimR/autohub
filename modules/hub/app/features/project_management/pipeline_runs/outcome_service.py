"""Project persisted evidence only; never infer current authority from a receipt."""

from .outcome_repo import DecisionOutcomeRepository


class DecisionOutcomeService:
    def __init__(self):
        self.repo = DecisionOutcomeRepository()

    async def evidence(self, session, run, request_id, operation) -> dict:
        row, question = await self.repo.record(session, run.id, request_id, operation)
        if row is None:
            return {"record_state": "unknown", "unavailable_reason": "No retained record for this request and owner"}
        result: dict = {"record_state": "recorded", "unavailable_reason": "Unsupported or absent facts remain unknown"}
        attempt_id = None
        if operation == "question":
            result["question_id"] = row.id
        elif operation == "answer":
            assert question is not None
            result.update(question_id=question.id, answer_id=row.id, answer_text=row.answer)
            attempt_id = row.applied_attempt_id
        else:
            attempt_id = row.execution_attempt_id
        attempt, delivery = await self.repo.attempt(session, run.id, attempt_id)
        if attempt:
            result.update(
                applied_attempt_id=attempt.id,
                execution_state=attempt.state,
                delivery_state="posted" if delivery and delivery.posted_at else "pending",
                delivery_at=delivery.posted_at if delivery else None,
            )
        return result
