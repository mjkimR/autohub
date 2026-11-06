"""Match answer publication against the immutable original worker question."""

from app.features.project_management.pipeline_runs.models import RunResumeReceipt
from sqlalchemy import select


def matching_publication(data: dict, progress: dict) -> dict | None:
    context = data.get("subject_context") or {}
    if not context.get("head_sha") or context.get("workflow") is None or context.get("segment") is None:
        return None
    request = (data.get("workflow_answer") or {}).get("request")
    records = [
        r
        for r in data.get("decision_records") or []
        if r.get("kind") == "answer-envelope" and (r.get("operation") or {}).get("request") == request
    ]
    # Each resume receipt captures only the operation whose ID matches its request.
    for record in records:
        if str(record.get("id")) != str(data.get("owner_request_id")):
            continue
        for resolution in progress.get("answer_resolutions") or []:
            if (
                resolution.get("answers_to") == record.get("answers_to")
                and resolution.get("question") == record.get("question")
                and resolution.get("workflow") == context["workflow"]
                and resolution.get("segment") == context["segment"]
                and progress.get("head_sha")
            ):
                return {**resolution, "inspected_head": progress["head_sha"]}
    return None


async def retain_publications(session, run_id, evidence: dict) -> None:
    receipts = await session.scalars(
        select(RunResumeReceipt).where(
            RunResumeReceipt.pipeline_run_id == run_id, RunResumeReceipt.decision_evidence.is_not(None)
        )
    )
    for receipt in receipts:
        data = receipt.decision_evidence or {}
        if data.get("answer_publication"):
            continue
        match = matching_publication({**data, "owner_request_id": str(receipt.id)}, evidence)
        if match:
            receipt.decision_evidence = {**data, "answer_publication": match}
