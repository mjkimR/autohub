"""Maintain discovery in the owner's SQL transaction, including direct ORM users.

Mapper hooks use their transaction connection and never commit or call providers.
Each changed run/question/receipt recomputes only its own bounded owner subjects.
"""

from types import SimpleNamespace
from typing import cast

from app.features.project_management.pipeline_runs.models import (
    DecisionEntry,
    PipelineRun,
    RunQuestion,
    RunResumeReceipt,
)
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.sdd.execution import retired
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import Table, delete, event, select
from sqlalchemy.orm import object_session
from sqlalchemy.orm.attributes import set_committed_value


def sync_run(connection, run_id, now=None):
    """Refresh one run's rows and return whether any of them is actionable."""
    run_row = connection.execute(select(PipelineRun.__table__).where(PipelineRun.id == run_id)).mappings().first()
    if run_row is None:
        return False
    run = SimpleNamespace(**run_row)
    now = now or get_current_utc_time()
    table = cast(Table, DecisionEntry.__table__)
    previous = {r["key"]: r for r in connection.execute(select(table).where(table.c.run_id == run_id)).mappings()}
    rows = []
    if run.state not in ("completed", "failed", "canceled") and not retired(run):
        questions = list(
            connection.execute(
                select(RunQuestion.__table__).where(
                    RunQuestion.pipeline_run_id == run_id, RunQuestion.state.in_(("open", "answered"))
                )
            ).mappings()
        )
        for question in questions:
            rows.append(
                dict(
                    kind="run-question",
                    subject_id=str(question["id"]),
                    fingerprint=request_digest(
                        {
                            "question": str(question["id"]),
                            "head": question["head_sha"],
                        }
                    ),
                    title=question["question"],
                    question_state=question["state"],
                    actionable=True,
                    waiting_since=question["created_at"],
                    head_sha=question["head_sha"],
                )
            )
    retained = set()
    for row in rows:
        key = f"{run_id}:{request_digest(dict(kind=row['kind'], subject=row['subject_id']))}"
        retained.add(key)
        old = previous.get(key)
        if old and old["fingerprint"] == row["fingerprint"]:
            row["waiting_since"] = old["waiting_since"]
        values = dict(**row, run_id=run_id, project_id=run.project_id, observed_at=now, revision=run.revision)
        if old:
            connection.execute(table.update().where(table.c.key == key).values(**values))
        else:
            connection.execute(table.insert().values(key=key, **values))
    obsolete = set(previous) - retained
    if obsolete:
        connection.execute(delete(table).where(table.c.key.in_(obsolete)))
    return any(row["actionable"] for row in rows)


def _sync(mapper, connection, owner):
    run_id = owner.id if isinstance(owner, PipelineRun) else owner.pipeline_run_id
    pending = sync_run(connection, run_id)
    # Keep the loaded run's read-only flag equal to the rows just written, without another statement.
    run = owner if isinstance(owner, PipelineRun) else None
    if run is None and (session := object_session(owner)) is not None:
        run = session.identity_map.get(session.identity_key(PipelineRun, run_id))
    if run is not None:
        set_committed_value(run, "has_pending_decision", pending)


for model in (PipelineRun, RunQuestion, RunResumeReceipt):
    event.listen(model, "after_insert", _sync)
    event.listen(model, "after_update", _sync)
    if model is not PipelineRun:
        event.listen(model, "after_delete", _sync)
