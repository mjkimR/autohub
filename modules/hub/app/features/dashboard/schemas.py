from app.features.project_management.pipeline_runs.models import PipelineRunState
from pydantic import BaseModel


class DashboardStats(BaseModel):
    project_count: int
    schedule_count: int
    connector_count: int
    active_connector_count: int
    total_runs: int
    runs_by_state: dict[PipelineRunState, int]
