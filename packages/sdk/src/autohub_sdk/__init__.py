"""Declare local pipelines and remote flow contracts; execution belongs to Auto Hub."""

from .client import AutoHubClient, AutoHubError
from .flow import ApprovalStep, FlowManifest, FlowSpec, InputRef, LiteralValue, TaskRef, TaskStep
from .manifest import Manifest, PipelineSpec
from .pipeline import Pipeline, pipeline
from .registry import Registry
from .remote import (
    ActivationReceipt,
    ActivationRequest,
    AttemptView,
    ErrorResponse,
    ReleaseReceipt,
    ReleaseSpec,
    RunCommand,
    RunRequest,
    RunView,
    TaskBinding,
    content_digest,
)

__all__ = [
    "ActivationReceipt",
    "ActivationRequest",
    "ApprovalStep",
    "AttemptView",
    "AutoHubClient",
    "AutoHubError",
    "ErrorResponse",
    "FlowManifest",
    "FlowSpec",
    "InputRef",
    "LiteralValue",
    "Manifest",
    "Pipeline",
    "PipelineSpec",
    "Registry",
    "ReleaseReceipt",
    "ReleaseSpec",
    "RunCommand",
    "RunRequest",
    "RunView",
    "TaskBinding",
    "TaskRef",
    "TaskStep",
    "content_digest",
    "pipeline",
]
