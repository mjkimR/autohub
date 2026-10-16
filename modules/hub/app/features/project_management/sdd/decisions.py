"""Adapt engine requests to durable Hub decisions without granting repository files merge authority."""

import json
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError

from .gates import INTEGRATION_REQUEST


def validate_answer(evidence: dict, answer: dict) -> dict:
    request = next((r for r in evidence["current"].get("requests", []) if r["id"] == answer["request"]), None)
    if request is None:
        raise ProjectError(409, "Workflow request is no longer open; reload the run")
    if request["id"] == INTEGRATION_REQUEST:
        raise ProjectError(422, "Use the integration approval controls for this request")
    if request.get("answer") == "envelope" or request["id"].startswith("question:"):
        raise ProjectError(
            422, "Worker questions are answered with an answer envelope on the pull request, not by a Hub decision"
        )
    value = answer.get("value")
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


def publication_instructions(evidence: dict) -> str:
    records = evidence.get("decision_records", [])
    if not records:
        return ""
    return (
        "\nPublish these devkit-authored decision records in the bound unit before doing stage work. "
        "They are durable Hub operator decisions. Idempotency: if a decisions/*.yaml record already contains "
        "the same autohub-decision UUID, do not write it again. Never overwrite an occupied filename; "
        "use the next free NN filename for the same request. Preserve the exact YAML content. "
        "For an accepted handoff, apply devkit workflow handoff --unit <unit> after publishing its record. "
        "Commit the records with the work; run devkit workflow next again. A return invalidates later approvals "
        "and reports: regenerate the affected evidence. Stop before merge.\n" + json.dumps(records, ensure_ascii=False)
    )
