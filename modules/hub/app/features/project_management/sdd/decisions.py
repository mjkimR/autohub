"""Adapt engine requests to durable Hub decisions without granting repository files merge authority."""

import json
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError

from .gates import INTEGRATION_REQUEST


def is_question(request: dict) -> bool:
    """A worker question: answered by an answer envelope the agent writes, never by a decision record."""
    return request.get("answer") == "envelope" or str(request.get("id", "")).startswith("question:")


def validate_answer(evidence: dict, answer: dict) -> dict:
    request = next((r for r in evidence["current"].get("requests", []) if r["id"] == answer["request"]), None)
    if request is None:
        raise ProjectError(409, "Workflow request is no longer open; reload the run")
    if request["id"] == INTEGRATION_REQUEST:
        raise ProjectError(422, "Use the integration approval controls for this request")
    value = answer.get("value")
    if is_question(request):
        if answer["action"] != "accept":
            raise ProjectError(422, "A worker question is answered, never declined or deferred; record the answer")
        options = [o["id"] for o in request.get("options") or []]
        if value is not None and value not in options:
            raise ProjectError(422, "Choose one of the question's options, or answer outside them with a decision")
        if value is None and not str(answer.get("note") or "").strip():
            raise ProjectError(422, "Write the decision for this question")
        return request
    if answer["action"] == "accept" and request["kind"] == "choose":
        if not any(o["id"] == value and o["eligible"] for o in request["options"]):
            raise ProjectError(422, "Choose an eligible workflow option")
    elif value is not None:
        raise ProjectError(422, "This request does not accept a choice value")
    return request


async def prepare_record(root: Path, unit: str, operation: dict, cli) -> dict:
    """Use devkit to author the record in the disposable checkout, never a second YAML writer."""
    note = f"autohub-decision:{operation['id']} {operation.get('note') or ''}"
    if operation.get("return_to"):
        args = ["return", "--to", operation["return_to"]]
    else:
        args = ["answer", "--request", operation["request"], "--action", operation["action"]]
        if operation.get("value") is not None:
            args += ["--value", operation["value"]]
    result = await cli(root, "workflow", *args, "--unit", unit, "--by", operation["actor"], "--note", note)
    path = Path(result["file"])
    # devkit returns a unit-relative path; never accept an out-of-unit write artifact.
    if path.is_absolute() or path.parts[:1] != ("decisions",) or ".." in path.parts:
        raise ProjectError(422, "Unsupported decision record path")
    record_path = root / unit / path
    if record_path.resolve() != record_path.absolute():
        raise ProjectError(422, "Decision records cannot use symlinks")
    transition = None
    if operation.get("request") == "handoff" and operation.get("action") == "accept":
        definition = await cli(root, "workflow", "show", operation["value"])
        if not definition.get("ok") or definition.get("anchor") != "spec.md":
            raise ProjectError(422, "This handoff needs a different work unit; enroll it separately")
        transition = {"workflow_id": definition["id"], "workflow_hash": definition["hash"]}
    return {
        "authorized_workflow": transition,
        "id": operation["id"],
        "file": path.as_posix(),
        "content": record_path.read_text(),
        "operation": operation,
    }


def answer_envelope_record(operation: dict, request: dict) -> dict:
    """The answer Hub recorded for a worker question; the agent writes it as an answer envelope, Hub never does."""
    target = str((request.get("target") or {}).get("name") or "")
    source, _, question = target.partition("#")
    if not source or not question:
        worker, _, question = str(request["id"]).removeprefix("question:").partition(".")
        source = f"{worker}.yaml"
    return {
        "kind": "answer-envelope",
        "id": operation["id"],
        "answers_to": source,
        "question": question,
        "choice": operation.get("value"),
        "decision": str(operation.get("note") or ""),
        "operation": operation,
    }


def publication_instructions(evidence: dict) -> str:
    records = evidence.get("decision_records", [])
    files = [r for r in records if r.get("kind") != "answer-envelope"]
    answers = [r for r in records if r.get("kind") == "answer-envelope"]
    text = ""
    if answers:
        unit = (evidence.get("snapshot") or {}).get("spec_dir", "<unit>")
        grouped: dict[str, list[dict]] = {}
        for record in answers:
            grouped.setdefault(record["answers_to"], []).append(
                {"question": record["question"], "choice": record["choice"], "decision": record["decision"]}
            )
        text += (
            "\nRecord these operator answers to worker questions as answer envelopes in the bound unit before doing "
            f"stage work: devkit workflow envelope answer --unit {unit} --answers-to <worker file> --answers-file "
            "<yaml list of the answers>, one envelope per worker file, never YAML by hand. Idempotency: if an "
            "answer envelope already answers the same question, do not write another. Commit the envelopes with the "
            "work; run devkit workflow next again. Stop before merge.\n"
            + json.dumps([{"answers_to": k, "answers": v} for k, v in grouped.items()], ensure_ascii=False)
        )
    if files:
        text += _record_instructions(files)
    return text


def _record_instructions(records: list[dict]) -> str:
    return (
        "\nPublish these devkit-authored decision records in the bound unit before doing stage work. "
        "They are durable Hub operator decisions. Idempotency: if a decisions/*.yaml record already contains "
        "the same autohub-decision UUID, do not write it again. Never overwrite an occupied filename; "
        "use the next free NN filename for the same request. Preserve the exact YAML content. "
        "For an accepted handoff, apply devkit workflow handoff --unit <unit> after publishing its record. "
        "Commit the records with the work; run devkit workflow next again. A return invalidates later approvals "
        "and reports: regenerate the affected evidence. Stop before merge.\n" + json.dumps(records, ensure_ascii=False)
    )
