"""Pure discovery adapter using the native owner's decision predicates."""

from .decisions import is_question
from .gates import INTEGRATION_REQUEST, PLAN_ACCEPT_REQUEST


def candidates(run, questions, receipts):
    from .progress import approval_gate, awaiting_review, held

    if (run.sdd_snapshot or {}).get("provider") != "devkit-spec":
        return []
    evidence = run.sdd_progress or {}
    requests = (evidence.get("current") or {}).get("requests") or []
    recorded = {
        str((r.get("operation") or {}).get("request")): r
        for r in evidence.get("decision_records") or []
        if r.get("kind") == "answer-envelope"
    }
    rows = []
    resolved = {(r.get("answers_to"), r.get("question")) for r in evidence.get("answer_resolutions") or []}
    pending_ids = set()
    for identity, record in recorded.items():
        if (record.get("answers_to"), record.get("question")) in resolved:
            continue
        pending_ids.add(identity)
        original = next(
            (r for r in requests if r.get("id") == identity), {"title": "Answer publication pending", "id": identity}
        )
        rows.append(("native-worker-question", identity, original, False))
    for request in requests:
        identity = str(request.get("id") or "")
        question = is_question(request)
        if identity in pending_ids or (question and identity in recorded):
            continue
        if run.state not in ("paused", "blocked") or questions:
            continue
        if question:
            rows.append(("native-worker-question", identity, request, True))
        elif held(evidence):
            continue
        elif identity == INTEGRATION_REQUEST:
            continue  # approval_gate below is the single authority predicate.
        elif identity == PLAN_ACCEPT_REQUEST:
            publishing = any(
                (r.get("publication") or {}).get("state") in ("preparing", "prepared", "uncertain", "published")
                for r in receipts
                if r
            )
            if not awaiting_review(evidence) and not evidence.get("plan_decision") and not publishing:
                rows.append(("native-proposal", identity, request, True))
        elif request.get("kind") in ("approve", "choose") and request.get("answer", "record") == "record":
            rows.append(("native-workflow", identity, request, True))
    if (
        run.state in ("paused", "blocked")
        and not questions
        and not evidence.get("approval")
        and not evidence.get("plan_decision")
        and approval_gate(evidence)
    ):
        rows.append(("native-integration", INTEGRATION_REQUEST, {"title": "Integration decision"}, True))
    return rows
