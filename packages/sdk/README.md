# Auto Hub SDK

An experimental, standalone Python package for declaring pipelines, validating
local execution, exporting a catalog, and declaring remote task/flow contracts. It depends only on Pydantic at runtime.
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

## Remote task and flow contracts

Version 0.2.0 adds a synchronous `AutoHubClient` using the standard library,
`FlowManifest` version 2, `FlowSpec`, `TaskStep`, `ApprovalStep`, release/binding
models, and run/command models. Version-1 `Manifest` and local `@pipeline`
behavior are unchanged. The actual Auto Hub backend does not serve these new
remote APIs yet; Plan Hub's local mock validates the client contract.

A flow declares ordered steps, task references, a result step, and JSON Schemas.
Task inputs use `LiteralValue` or `InputRef` from run inputs or earlier task
outputs. Approval may return to an earlier task under a declared rework limit.
Duplicate IDs/contracts, unknown task references, future output references, and
incomplete deployment bindings are rejected. Runtime field resolution and schema
validation belong to the host; the SDK does not prove schema assignability.

```python
from autohub_sdk import AutoHubClient, RunCommand, RunRequest, TaskRef

client = AutoHubClient("http://127.0.0.1:8091", api_key="local-mock-only")
# ReleaseSpec contains FlowManifest and a binding for every task; no Python upload.
# client.register_release("planhub", "local", "release-1", release)
# client.activate_release("planhub", "local", "release-1", expected_revision=0)
run = client.start_run(
    RunRequest(
        provider="planhub",
        environment="local",
        task=TaskRef(key="planhub.delivery"),
        inputs={"message": "example"},
        idempotency_key="request-1",
    )
)
if run.waiting_reason == "approval":
    run = client.command(
        run.run_id,
        RunCommand(
            command_id="approval-1",
            expected_revision=run.revision,
            action="approve",
        ),
    )
```

This snippet assumes the mock is running with a registered, active sample
release. A configured API key is sent through `X-API-Key`, matching the existing
host authentication convention. The local demo key is not a real service identity.
`AutoHubError` exposes HTTP status and structured error code. Network errors and
timeouts propagate; there are no automatic retries. Reconcile a failed response
using the same run request key/command ID before creating new work. Redirects
are not followed, avoiding credential forwarding to other hosts.

See [remote contract](../../docs/sdk-task-flow.md) for endpoints and ownership.
There is no startup hook, code scanning, scheduler, worker deployment, or durable
step recovery engine in the SDK. Declaration registration does not deploy code.

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
