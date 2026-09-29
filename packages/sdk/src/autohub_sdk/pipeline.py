"""An async function and its validated input/output contract."""

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast, get_type_hints

from pydantic import BaseModel

from .manifest import PipelineSpec


@dataclass(frozen=True)
class Pipeline[InputT: BaseModel, OutputT: BaseModel]:
    """A local callable. Calling it performs no retries or remote registration."""

    key: str
    contract_version: int
    title: str
    description: str
    input_model: type[InputT]
    output_model: type[OutputT]
    _handler: Callable[[InputT], Awaitable[OutputT]]

    async def __call__(self, inputs: InputT | dict[str, Any]) -> OutputT:
        validated = self.input_model.model_validate(inputs)
        result = await self._handler(validated)
        return self.output_model.model_validate(result)

    def spec(self) -> PipelineSpec:
        """Return fresh schemas so callers cannot mutate future exports."""
        return PipelineSpec(
            key=self.key,
            contract_version=self.contract_version,
            title=self.title,
            description=self.description,
            input_schema=self.input_model.model_json_schema(mode="validation"),
            output_schema=self.output_model.model_json_schema(mode="serialization"),
        )


def pipeline(*, key: str, contract_version: int, title: str | None = None):
    """Wrap one async function annotated with a Pydantic input and output model.

    Definitions must resolve through the function's module globals. Use one
    required positional parameter; keyword-only parameters and injected context
    are not part of this initial contract.
    """

    def decorate[InputT: BaseModel, OutputT: BaseModel](
        handler: Callable[[InputT], Awaitable[OutputT]],
    ) -> Pipeline[InputT, OutputT]:
        if not inspect.iscoroutinefunction(handler):
            raise TypeError("A pipeline must be an async function")
        parameters = list(inspect.signature(handler).parameters.values())
        if (
            len(parameters) != 1
            or parameters[0].kind not in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            or parameters[0].default is not inspect.Parameter.empty
        ):
            raise TypeError("A pipeline must accept exactly one required positional input")
        hints = get_type_hints(handler)
        input_model = hints.get(parameters[0].name)
        output_model = hints.get("return")
        for label, model in (("input", input_model), ("output", output_model)):
            if not inspect.isclass(model) or not issubclass(model, BaseModel) or model is BaseModel:
                raise TypeError(f"Pipeline {label} annotation must be a concrete Pydantic model")
        definition = Pipeline(
            key=key,
            contract_version=contract_version,
            title=title if title is not None else key,
            description=inspect.getdoc(handler) or "",
            input_model=cast(type[InputT], input_model),
            output_model=cast(type[OutputT], output_model),
            _handler=handler,
        )
        definition.spec()  # Fail invalid metadata or unsupported schemas at declaration time.
        return definition

    return decorate
