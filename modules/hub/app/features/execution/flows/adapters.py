"""Allowlisted worker bindings and an idempotent worker protocol; no code upload."""

import os
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from app_http_client import get_http_client
from autohub_sdk import ReleaseSpec, TaskRef, content_digest
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import FlowError


class HttpTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    base_url: str
    credential_env: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]*$")

    @model_validator(mode="after")
    def check_url(self):
        url = urlsplit(self.base_url)
        local = url.hostname in ("localhost", "127.0.0.1", "::1")
        if (url.scheme != "https" and not (url.scheme == "http" and local)) or not url.hostname:
            raise ValueError("worker URL requires HTTPS or loopback HTTP")
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("worker URL cannot contain credentials, query or fragment")
        return self


class WorkerBindings:
    def __init__(self, targets: dict[str, HttpTarget] | None = None):
        self.targets = targets or {}

    def resolve(self, release: ReleaseSpec) -> dict:
        resolved = {}
        for binding in release.bindings:
            key = f"{binding.task.key}@{binding.task.contract_version}"
            if binding.executor == "native" and binding.target == "autohub.identity":
                resolved[key] = {"executor": "native", "target": binding.target}
            elif binding.executor == "http" and binding.target in self.targets:
                resolved[key] = {
                    "executor": "http",
                    "target": binding.target,
                    **self.targets[binding.target].model_dump(),
                }
            else:
                raise FlowError(422, "worker-binding", "executor target is not configured on this host")
        return resolved


def get_worker_bindings() -> WorkerBindings:
    from pydantic import TypeAdapter

    targets = TypeAdapter(dict[str, HttpTarget]).validate_json(os.getenv("AUTOHUB_FLOW_HTTP_TARGETS", "{}"))
    return WorkerBindings(targets)


class WorkerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attempt_id: UUID
    status: Literal["pending", "completed", "failed", "canceled", "not_found"]
    output: dict[str, Any] | None = None
    error: str | None = None

    @model_validator(mode="after")
    def check_output(self):
        content_digest(self.output)
        if self.status == "completed" and self.output is None:
            raise ValueError("completed worker result requires output")
        return self


@dataclass(frozen=True)
class WorkerAction:
    run_id: UUID
    attempt_id: UUID
    revision: int
    operation: Literal["submit", "inspect", "cancel"]
    task: TaskRef
    inputs: dict
    binding: dict
    release_id: str
    release_digest: str


class WorkerAdapter:
    async def execute(self, action: WorkerAction) -> WorkerResult:
        if action.binding["executor"] == "native":
            return WorkerResult(
                attempt_id=action.attempt_id,
                status="canceled" if action.operation == "cancel" else "completed",
                output=None if action.operation == "cancel" else action.inputs,
            )
        target = HttpTarget.model_validate({key: action.binding[key] for key in ("base_url", "credential_env")})
        headers = {"Idempotency-Key": str(action.attempt_id)}
        if target.credential_env:
            credential = os.getenv(target.credential_env)
            if not credential:
                raise FlowError(503, "worker-credentials", "worker credential configuration is unavailable")
            headers["X-API-Key"] = credential
        client = get_http_client()
        base = target.base_url.rstrip("/") + "/executions"
        if action.operation == "submit":
            response = await client.post(
                base,
                headers=headers,
                timeout=5,
                follow_redirects=False,
                json={
                    "attempt_id": str(action.attempt_id),
                    "run_id": str(action.run_id),
                    "task": action.task.model_dump(),
                    "inputs": action.inputs,
                    "release_id": action.release_id,
                    "release_digest": action.release_digest,
                },
            )
        elif action.operation == "cancel":
            response = await client.delete(
                f"{base}/{action.attempt_id}", headers=headers, timeout=5, follow_redirects=False
            )
        else:
            response = await client.get(
                f"{base}/{action.attempt_id}", headers=headers, timeout=5, follow_redirects=False
            )
            if response.status_code == 404:
                absent = WorkerResult.model_validate(response.json())
                if absent.attempt_id != action.attempt_id or absent.status != "not_found":
                    raise FlowError(503, "worker-protocol", "worker absence is not authoritative")
                return absent
        response.raise_for_status()
        result = WorkerResult.model_validate(response.json())
        if result.attempt_id != action.attempt_id or (result.status == "not_found" and action.operation != "inspect"):
            raise FlowError(503, "worker-protocol", "worker result does not match this attempt")
        return result


RECOVERABLE_ERRORS = (httpx.HTTPError, FlowError, ValueError)
