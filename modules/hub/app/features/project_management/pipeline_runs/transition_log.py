"""Logs every pipeline run state change from one place.

The lifecycle changes a run's state at dozens of sites. Listening on the mapper instead of logging at each site
covers all of them, including ones written later. Statements that bypass the ORM (lease and notice bookkeeping)
never change a run's state, so nothing is missed.
"""

from app.features.project_management.pipeline_runs.models import PipelineRun
from app_layer_base.core.log import logger
from sqlalchemy import event, inspect


def _changed(run: PipelineRun, attribute: str) -> tuple[object, object] | None:
    history = inspect(run).attrs[attribute].history
    if not history.has_changes():
        return None
    return (history.deleted[0] if history.deleted else None, history.added[0] if history.added else None)


@event.listens_for(PipelineRun, "after_insert")
def _log_enrollment(mapper, connection, run: PipelineRun) -> None:
    logger.info(f"run {run.id} enrolled: {run.github_repository}#{run.pull_number} state={run.state}")


@event.listens_for(PipelineRun, "after_update")
def _log_transition(mapper, connection, run: PipelineRun) -> None:
    state = _changed(run, "state")
    reason = _changed(run, "pause_reason")
    if state is None and reason is None:
        return
    before, after = state if state is not None else (run.state, run.state)
    reason_note = f" reason: {run.pause_reason}" if run.pause_reason else ""
    logger.info(
        f"run {run.id} {run.github_repository}#{run.pull_number}: {before} -> {after} "
        f"(revision {run.revision}){reason_note}"
    )
