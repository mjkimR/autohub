"""Declare pipelines, execute locally, and export their contracts without a server."""

from .manifest import Manifest, PipelineSpec
from .pipeline import Pipeline, pipeline
from .registry import Registry

__all__ = ["Manifest", "Pipeline", "PipelineSpec", "Registry", "pipeline"]
