"""Wire contracts shared by clients and hosts; execution state belongs to the host."""

import hashlib
import json
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from .flow import ContractModel, FlowManifest, Identifier, TaskRef

Revision = Annotated[int, Field(ge=0, strict=True)]
RequestId = Annotated[str, Field(min_length=1, max_length=128)]


def content_digest(value: Any) -> str:
    """Digest canonical JSON, rejecting NaN rather than producing non-JSON payloads."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


class TaskBinding(ContractModel):
    task: TaskRef
    executor: Literal["http", "native"]
    target: str = Field(min_length=1)


class ReleaseSpec(ContractModel):
    manifest: FlowManifest
    bindings: tuple[TaskBinding, ...]

    @model_validator(mode="after")
    def check_bindings(self) -> Self:
        expected = {(task.key, task.contract_version) for task in self.manifest.tasks}
        actual = [(binding.task.key, binding.task.contract_version) for binding in self.bindings]
        if len(set(actual)) != len(actual) or set(actual) != expected:
            raise ValueError("Exactly one binding is required for every task contract")
        return self

    def digest(self) -> str:
        return content_digest(self.model_dump(mode="python"))


class ReleaseReceipt(ContractModel):
    provider: Identifier
    environment: Identifier
    release_id: RequestId
    digest: str


class ActivationRequest(ContractModel):
    expected_revision: Revision


class ActivationReceipt(ReleaseReceipt):
    revision: Revision


class RunRequest(ContractModel):
    provider: Identifier
    environment: Identifier
    task: TaskRef
    inputs: dict[str, Any]
    idempotency_key: RequestId


class RunCommand(ContractModel):
    command_id: RequestId
    expected_revision: Revision
    action: Literal["approve", "revise", "cancel", "resume"]


class AttemptView(ContractModel):
    step_id: Identifier
    number: Annotated[int, Field(ge=1, strict=True)]
    status: Literal["running", "observing", "completed", "failed", "canceled"]
    inputs: dict[str, Any]
    output: dict[str, Any] | None = None
    error: str | None = None


class RunView(ContractModel):
    run_id: str
    provider: Identifier
    environment: Identifier
    release_id: RequestId
    release_digest: str
    task: TaskRef
    revision: Revision
    status: Literal["queued", "running", "waiting", "failed", "canceling", "canceled", "completed"]
    current_step: Identifier | None = None
    waiting_reason: str | None = None
    attempts: tuple[AttemptView, ...] = ()
    output: dict[str, Any] | None = None
    error: str | None = None


class ErrorResponse(ContractModel):
    code: str
    message: str
