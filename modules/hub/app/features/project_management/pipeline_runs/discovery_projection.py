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
from app.features.project_management.sdd.discovery import candidates
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import Table, delete, event, select


def sync_run(connection, run_id, now=None):
    run_row = connection.execute(select(PipelineRun.__table__).where(PipelineRun.id == run_id)).mappings().first()
    if run_row is None:
        return
    run = SimpleNamespace(**run_row)
    now = now or get_current_utc_time()
    table = cast(Table, DecisionEntry.__table__)
    previous = {r["key"]: r for r in connection.execute(select(table).where(table.c.run_id == run_id)).mappings()}
    rows = []
    if run.state not in ("completed", "failed", "canceled") and (
        not run.sdd_snapshot or run.sdd_snapshot.get("provider") == "devkit-spec"
    ):
        questions = list(
            connection.execute(
                select(RunQuestion.__table__).where(
                    RunQuestion.pipeline_run_id == run_id, RunQuestion.state.in_(("open", "answered"))
                )
            ).mappings()
        )
        native = (run.sdd_snapshot or {}).get("provider") == "devkit-spec"
        for question in questions:
            rows.append(
                dict(
                    kind="native-hub-question" if native else "run-question",
                    subject_id=str(question["id"]),
                    fingerprint=request_digest({"question": str(question["id"]), "head": question["head_sha"]}),
                    title=question["question"],
                    question_state=question["state"],
                    actionable=True,
                    waiting_since=question["created_at"],
                    head_sha=question["head_sha"],
                )
            )
        receipts = list(
            connection.execute(
                select(RunResumeReceipt.decision_evidence).where(RunResumeReceipt.pipeline_run_id == run_id)
            ).scalars()
        )
        progress = run.sdd_progress or {}
        for kind, subject, request, actionable in candidates(run, questions, receipts):
            fingerprint = request_digest(
                {
                    "request": request,
                    "head": progress.get("head_sha"),
                    "base": progress.get("base_sha"),
                    "snapshot": run.sdd_snapshot,
                    "workflow": progress.get("workflow"),
                    "binding": [str(run.github_connector_id), run.github_repository, run.project_revision],
                }
            )
            rows.append(
                dict(
                    kind=kind,
                    subject_id=subject,
                    fingerprint=fingerprint,
                    title=str(request.get("title") or subject),
                    question_state=None,
                    actionable=actionable,
                    waiting_since=now,
                    head_sha=progress.get("head_sha"),
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


def _sync(mapper, connection, owner):
    sync_run(connection, owner.id if isinstance(owner, PipelineRun) else owner.pipeline_run_id)


for model in (PipelineRun, RunQuestion, RunResumeReceipt):
    event.listen(model, "after_insert", _sync)
    event.listen(model, "after_update", _sync)
    if model is not PipelineRun:
        event.listen(model, "after_delete", _sync)
