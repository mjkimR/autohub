# Auto Hub SDK

An experimental, standalone Python package for declaring pipelines, validating
local execution, and exporting a catalog. It depends only on Pydantic at runtime.
The API is provisional until the first real consumer pipeline validates it.

The distribution is `autohub-sdk`; import it as `autohub_sdk`. Python 3.13 or newer
is required. No release has been published yet. The backend does not depend on
this package, and rside is not connected to it yet.

## Declare and execute

```python
from autohub_sdk import Registry, pipeline
from pydantic import BaseModel, ConfigDict


class GreetingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str


class GreetingOutput(BaseModel):
    message: str


@pipeline(key="example.greeting", contract_version=1, title="Greeting")
async def greet(inputs: GreetingInput) -> GreetingOutput:
    """Create a greeting locally."""
    return GreetingOutput(message=f"Hello, {inputs.name}!")


catalog = Registry([greet])
print(catalog.manifest().to_json())
# In an async caller: result = await greet({"name": "World"})
```

Use an async function with exactly one required positional input, annotated with
a concrete Pydantic model, and a concrete Pydantic return model. Annotations must
resolve in the function's module namespace. Postponed annotations are supported.
Input coercion, aliases, extra fields, and constraints follow the models' Pydantic
configuration. Inputs and outputs are validated; handler exceptions propagate
without retries. Existing model instances follow Pydantic's `revalidate_instances`
setting; use `"always"` when instances can have been mutated or constructed without
validation. A returned model's JSON representation follows its serialization
schema.

`@pipeline` returns a callable `Pipeline` definition. It does not add that
definition to a global registry. Explicit `Registry([...])` membership determines
what is exported. Duplicate `(key, contract_version)` pairs are rejected; different
versions can coexist. Export does not execute pipeline handlers or contact a server.

## Manifest

`Registry.manifest()` returns a version-1 `Manifest` with sorted task definitions:
`key`, `contract_version`, `title`, `description`, `input_schema`, and `output_schema`.
Descriptions default to function docstrings; titles default to keys. Input schemas
use validation mode and output schemas use serialization mode, following
[Pydantic's schema modes](https://docs.pydantic.dev/latest/concepts/json_schema/).
`to_json()` produces stable, sorted JSON without timestamps. Each export creates
fresh schemas. This is a definition manifest, not a deployed release manifest:
environment, credentials, image digests, and Cloud Run targets are not included.

There is no registration API client, startup hook, code scanning, scheduler,
remote execution adapter, or step recovery engine in this package.

## Development

Run from the repository root:

```sh
just init sdk
just lint sdk
just check sdk
just test-sdk
just build-sdk
uv run --no-active --no-sync python packages/sdk/examples/greeting.py --name World
uv run --no-active --no-sync python packages/sdk/examples/greeting.py --manifest
```

`just init sdk` prepares the shared workspace environment. SDK tests do not import
backend fixtures or require databases. Wheel and source artifacts are built into
the root `dist/` directory. Packaging and the workspace share the root `uv.lock`;
see [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/).
