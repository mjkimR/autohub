from typing import Annotated

from app.features.configuration.connectors.usecases.token import ReadConnectorTokenUseCase
from app.features.project_management.pipelines.services import PipelineObservationService
from fastapi import Depends


def get_pipeline_observer(tokens: Annotated[ReadConnectorTokenUseCase, Depends()]) -> PipelineObservationService:
    return PipelineObservationService(tokens.execute)
