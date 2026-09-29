"""Run a local example or print its manifest; no network or archive writes."""

import argparse
import asyncio

from autohub_sdk import Registry, pipeline
from pydantic import BaseModel, ConfigDict, Field


class GreetingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)


class GreetingOutput(BaseModel):
    message: str


@pipeline(key="example.greeting", contract_version=1, title="Greeting")
async def greet(inputs: GreetingInput) -> GreetingOutput:
    """Create a greeting locally."""
    return GreetingOutput(message=f"Hello, {inputs.name}!")


catalog = Registry([greet])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--name", default="World")
    args = parser.parse_args()
    if args.manifest:
        print(catalog.manifest().to_json())
    else:
        print(asyncio.run(greet({"name": args.name})).model_dump_json())


if __name__ == "__main__":
    main()
