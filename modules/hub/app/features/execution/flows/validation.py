from typing import Any

from autohub_sdk import ApprovalStep, FlowSpec, LiteralValue, ReleaseSpec, TaskRef, TaskStep, content_digest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from referencing.exceptions import Unresolvable

from .errors import FlowError


def local_refs(value):
    if isinstance(value, dict):
        for key in ("$ref", "$dynamicRef"):
            if key in value and (not isinstance(value[key], str) or not value[key].startswith("#")):
                raise FlowError(422, "schema-reference", "schemas must use local references")
        for nested in value.values():
            local_refs(nested)
    elif isinstance(value, list):
        for nested in value:
            local_refs(nested)


def digest(value) -> str:
    try:
        return content_digest(value)
    except (TypeError, ValueError) as exc:
        raise FlowError(422, "json-invalid", "payload must contain finite JSON values") from exc


def check_ref(ref):
    if len(ref.key) > 256 or ref.contract_version > 2147483647:
        raise FlowError(422, "contract-limit", "task key or version exceeds host limits")


def check_release(release: ReleaseSpec):
    for definition in (*release.manifest.tasks, *release.manifest.flows):
        check_ref(definition)
        if isinstance(definition, FlowSpec):
            for step in definition.steps:
                if len(step.id) > 128:
                    raise FlowError(422, "contract-limit", "step ID exceeds host limits")
                if isinstance(step, ApprovalStep) and step.deadline_seconds > 31536000:
                    raise FlowError(422, "contract-limit", "approval deadline exceeds one year")
        for schema in (definition.input_schema, definition.output_schema):
            local_refs(schema)
            try:
                Draft202012Validator.check_schema(schema)
            except SchemaError as exc:
                raise FlowError(422, "schema-invalid", "invalid JSON Schema") from exc


def validate(schema: dict, value: Any):
    try:
        Draft202012Validator(schema).validate(value)
    except (ValidationError, Unresolvable) as exc:
        # No input/output values in errors or logs.
        raise FlowError(422, "schema-invalid", "value does not match its JSON Schema") from exc


def definition(release: ReleaseSpec, ref: TaskRef):
    result = next(
        (
            item
            for item in (*release.manifest.tasks, *release.manifest.flows)
            if (item.key, item.contract_version) == (ref.key, ref.contract_version)
        ),
        None,
    )
    if result is None:
        raise FlowError(404, "task-not-found", "task contract is not in this release")
    return result


def steps_for(
    release: ReleaseSpec, ref: TaskRef, inputs: dict
) -> tuple[tuple[TaskStep | ApprovalStep, ...], str, dict]:
    item = definition(release, ref)
    if isinstance(item, FlowSpec):
        return item.steps, item.result_step, item.output_schema
    step = TaskStep(id="task", task=ref, inputs={key: LiteralValue(value=value) for key, value in inputs.items()})
    return (step,), "task", item.output_schema
