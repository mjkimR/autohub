from __future__ import annotations

import asyncio
import json
from decimal import Decimal

import pytest
from autohub_sdk import Registry, pipeline
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Inputs(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    count: int = Field(gt=0)


class Outputs(BaseModel):
    model_config = ConfigDict(revalidate_instances="always")
    total: Decimal


async def calculate(inputs: Inputs) -> Outputs:
    """Compute a total."""
    return Outputs(total=Decimal(inputs.count) * 2)


def test_local_validation_prevents_invalid_inputs_and_revalidates_models():
    calls = []

    @pipeline(key="example.calculate", contract_version=1)
    async def tracked(inputs: Inputs) -> Outputs:
        calls.append(inputs.count)
        return await calculate(inputs)

    assert asyncio.run(tracked({"count": 3})).total == 6
    invalid_model = Inputs.model_construct(count=-1)
    for invalid in ({"count": 0}, {"count": 1, "unknown": True}, invalid_model):
        with pytest.raises(ValidationError):
            asyncio.run(tracked(invalid))
    assert calls == [3]


def test_invalid_output_is_rejected():
    @pipeline(key="example.invalid", contract_version=1)
    async def invalid(inputs: Inputs) -> Outputs:
        return Outputs.model_construct(total="not-a-number")

    with pytest.raises(ValidationError):
        asyncio.run(invalid({"count": 1}))


def test_export_is_sorted_and_does_not_execute_handlers():
    @pipeline(key="example.z", contract_version=1, title="계산")
    async def never_run(inputs: Inputs) -> Outputs:
        """Export only."""
        raise AssertionError("Export must not execute pipelines")

    other = pipeline(key="example.a", contract_version=2)(calculate)
    first = Registry([never_run, other]).manifest().to_json()
    second = Registry([other, never_run]).manifest().to_json()
    assert first == second
    manifest = json.loads(first)
    assert manifest["manifest_version"] == 1
    assert [task["key"] for task in manifest["tasks"]] == ["example.a", "example.z"]
    task = manifest["tasks"][1]
    assert task["description"] == "Export only."
    assert task["input_schema"]["required"] == ["count"]
    # Serialization schema describes Decimal's JSON string output, not its numeric input.
    assert task["output_schema"]["properties"]["total"]["type"] == "string"
    assert "계산" in first


def test_catalogs_are_explicit_and_exports_are_independent():
    definition = pipeline(key="example.calculate", contract_version=1)(calculate)
    catalog = Registry([definition])
    expected = catalog.manifest().to_json()
    catalog.manifest().tasks[0].input_schema.clear()
    assert catalog.manifest().to_json() == expected
    assert Registry().manifest().tasks == ()
    with pytest.raises(ValueError, match="Duplicate"):
        catalog.add(definition)
    catalog.add(pipeline(key="example.calculate", contract_version=2)(calculate))
    assert [task.contract_version for task in catalog.manifest().tasks] == [1, 2]


@pytest.mark.parametrize(
    "key, version", [("undotted", 1), ("example.bad key", 1), ("example.valid", 0), ("example.valid", True)]
)
def test_invalid_identity_is_rejected(key, version):
    with pytest.raises(ValidationError):
        pipeline(key=key, contract_version=version)(calculate)


def test_unsupported_signatures_fail_at_declaration():
    def sync(inputs: Inputs) -> Outputs:
        return Outputs(total=Decimal(1))

    async def keyword_only(*, inputs: Inputs) -> Outputs:
        return await calculate(inputs)

    async def missing_output(inputs: Inputs):
        return await calculate(inputs)

    async def scalar_input(inputs: int) -> Outputs:
        return Outputs(total=Decimal(inputs))

    for handler in (sync, keyword_only, missing_output, scalar_input):
        with pytest.raises(TypeError):
            pipeline(key="example.invalid", contract_version=1)(handler)  # type: ignore[arg-type]


def test_handler_failure_propagates_without_retry():
    calls = []

    @pipeline(key="example.failure", contract_version=1)
    async def failing(inputs: Inputs) -> Outputs:
        calls.append(inputs.count)
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError, match="failed"):
        asyncio.run(failing({"count": 1}))
    assert calls == [1]
