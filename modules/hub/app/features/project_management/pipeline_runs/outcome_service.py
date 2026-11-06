"""Project persisted evidence only; never infer current authority from a receipt."""

from .outcome_repo import DecisionOutcomeRepository


class DecisionOutcomeService:
    def __init__(self):
        self.repo = DecisionOutcomeRepository()

    async def evidence(self, session, run, request_id, operation):
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
            result.update(
                native_channel=workflow.get("request") or data.get("action"),
                publication_state=publication.get("state"),
                candidate_head=plan.get("commit_sha") or publication.get("candidate_sha"),
            )
            if workflow.get("request", "").startswith("question:"):
                result["publication_state"] = "pending"
                # The receipt's exact request identifies both source question envelope and question ID.
                progress = run.sdd_progress or {}
                context = progress.get("current") or {}
                record = next(
                    (
                        item
                        for item in data.get("decision_records") or []
                        if item.get("kind") == "answer-envelope"
                        and str(item.get("id")) == str(request_id)
                        and (item.get("operation") or {}).get("request") == workflow["request"]
                    ),
                    None,
                )
                for resolution in progress.get("answer_resolutions") or []:
                    if (
                        record
                        and resolution.get("answers_to") == record.get("answers_to")
                        and resolution.get("question") == record.get("question")
                        and resolution.get("workflow") == context.get("workflow")
                        and resolution.get("segment") == context.get("segment")
                        and progress.get("head_sha")
                    ):
                        result.update(publication_state="published", resolved_envelope=resolution.get("file"))
                        break
        attempt, delivery = await self.repo.attempt(session, run.id, attempt_id)
        if attempt:
            result.update(
                applied_attempt_id=attempt.id,
                execution_state=attempt.state,
                delivery_state="posted" if delivery and delivery.posted_at else "pending",
                delivery_at=delivery.posted_at if delivery else None,
            )
        return result
