"""A deliberately small, versioned sequential flow contract; no execution engine."""

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .manifest import PipelineSpec

Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]*$")]
TaskKey = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$")]
Version = Annotated[int, Field(gt=0, strict=True)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TaskRef(ContractModel):
    key: TaskKey
    contract_version: Version = 1


class LiteralValue(ContractModel):
    kind: Literal["literal"] = "literal"
    value: Any


class InputRef(ContractModel):
    kind: Literal["ref"] = "ref"
    source: Literal["run", "step"]
    step_id: Identifier | None = None
    path: tuple[str, ...] = ()

    @model_validator(mode="after")
    def check_source(self) -> Self:
        if (self.source == "step") != (self.step_id is not None):
            raise ValueError("step refs require step_id; run refs must omit it")
        return self


ValueBinding = Annotated[LiteralValue | InputRef, Field(discriminator="kind")]


class TaskStep(ContractModel):
    kind: Literal["task"] = "task"
    id: Identifier
    task: TaskRef
    inputs: dict[str, ValueBinding]
    max_attempts: Annotated[int, Field(ge=1, le=10, strict=True)] = 1


class ApprovalStep(ContractModel):
    kind: Literal["approval"] = "approval"
    id: Identifier
    deadline_seconds: Annotated[int, Field(ge=1, strict=True)] = 86400
    revise_to: Identifier | None = None
    max_revisions: Annotated[int, Field(ge=0, le=10, strict=True)] = 0

    @model_validator(mode="after")
    def check_revision(self) -> Self:
        if (self.revise_to is not None) != (self.max_revisions > 0):
            raise ValueError("revise_to and a positive max_revisions must be declared together")
        return self


StepSpec = Annotated[TaskStep | ApprovalStep, Field(discriminator="kind")]


class FlowSpec(ContractModel):
    key: TaskKey
    contract_version: Version = 1
    title: str = Field(min_length=1)
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    steps: tuple[StepSpec, ...] = Field(min_length=1)
    result_step: Identifier

    @model_validator(mode="after")
    def check_graph(self) -> Self:
        previous_tasks: set[str] = set()
        identifiers: set[str] = set()
        for step in self.steps:
            if step.id in identifiers:
                raise ValueError(f"Duplicate step ID: {step.id}")
            identifiers.add(step.id)
            if isinstance(step, TaskStep):
                for binding in step.inputs.values():
                    if (
                        isinstance(binding, InputRef)
                        and binding.source == "step"
                        and binding.step_id not in previous_tasks
                    ):
                        raise ValueError(f"Step input must reference an earlier task: {binding.step_id}")
                previous_tasks.add(step.id)
            elif step.revise_to is not None and step.revise_to not in previous_tasks:
                raise ValueError("revise_to must reference an earlier task")
        if self.result_step not in previous_tasks:
            raise ValueError("result_step must reference a task")
        return self


class FlowManifest(ContractModel):
    """Version 2 is separate from the unchanged local version-1 Manifest."""

    manifest_version: Literal[2] = 2
    tasks: tuple[PipelineSpec, ...]
    flows: tuple[FlowSpec, ...] = ()

    @model_validator(mode="after")
    def check_catalog(self) -> Self:
        task_ids = [(task.key, task.contract_version) for task in self.tasks]
        flow_ids = [(flow.key, flow.contract_version) for flow in self.flows]
        if len(set(task_ids + flow_ids)) != len(task_ids + flow_ids):
            raise ValueError("Duplicate task or flow contract")
        for flow in self.flows:
            for step in flow.steps:
                if isinstance(step, TaskStep) and (step.task.key, step.task.contract_version) not in task_ids:
                    raise ValueError(f"Unknown task contract: {step.task.key}")
        return self
