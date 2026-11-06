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
            data = row.decision_evidence or {}
            workflow = data.get("workflow_answer") or {}
            publication = data.get("publication") or {}
            plan = data.get("plan_decision") or {}
            candidates = list(
                dict.fromkeys(
                    c["commit_sha"]
                    for c in publication.get("candidates") or []
                    if isinstance(c, dict) and isinstance(c.get("commit_sha"), str)
                )
            )
            result["candidate_heads"] = candidates
            result.update(
                native_channel=workflow.get("request") or data.get("action"),
                publication_state=publication.get("state"),
                candidate_head=plan.get("commit_sha") or (candidates[0] if len(candidates) == 1 else None),
            )
            if workflow.get("request", "").startswith("question:"):
                result["publication_state"] = "pending"
                # The receipt's exact request identifies both source question envelope and question ID.
                from app.features.project_management.sdd.answer_publication import matching_publication

                proof = data.get("answer_publication") or matching_publication(
                    {**data, "owner_request_id": str(request_id)}, run.sdd_progress or {}
                )
                if proof:
                    result.update(publication_state="published", resolved_envelope=proof.get("file"))
                elif not data.get("subject_context"):
                    result["publication_state"] = None
                    result["unavailable_reason"] = "Original worker question context was not retained"
        attempt, delivery = await self.repo.attempt(session, run.id, attempt_id)
        if attempt:
            result.update(
                applied_attempt_id=attempt.id,
                execution_state=attempt.state,
                delivery_state="posted" if delivery and delivery.posted_at else "pending",
                delivery_at=delivery.posted_at if delivery else None,
            )
        return result
