"""Bounded keyset reads of persisted discovery; no provider access."""

from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES, DecisionEntry, PipelineRun
from app.features.project_management.projects.models import Project
from sqlalchemy import and_, func, or_, select


class DecisionDiscoveryRepository:
    @staticmethod
    def _filtered(statement, project_id, kind, question_state):
        statement = (
            statement.join(PipelineRun, PipelineRun.id == DecisionEntry.run_id)
            .join(Project, Project.id == DecisionEntry.project_id)
            .where(PipelineRun.state.not_in(FINAL_RUN_STATES))
        )
        if project_id is not None:
            statement = statement.where(DecisionEntry.project_id == project_id)
        if kind is not None:
            statement = statement.where(DecisionEntry.kind == kind)
        if question_state is not None:
            statement = statement.where(DecisionEntry.question_state == question_state)
        return statement

    async def page(self, session, project_id, kind, question_state, after, limit):
        statement = self._filtered(select(DecisionEntry, PipelineRun), project_id, kind, question_state)
        if after:
            timestamp, key = after
            statement = statement.where(
                or_(
                    DecisionEntry.waiting_since > timestamp,
                    and_(DecisionEntry.waiting_since == timestamp, DecisionEntry.key > key),
                )
            )
        return list(
            (
                await session.execute(
                    statement.order_by(DecisionEntry.waiting_since, DecisionEntry.key).limit(limit + 1)
                )
            ).all()
        )

    async def count_actionable(self, session, project_id, kind, question_state):
        statement = self._filtered(
            select(func.count(DecisionEntry.key)).select_from(DecisionEntry), project_id, kind, question_state
        ).where(DecisionEntry.actionable.is_(True))
        return (await session.execute(statement)).scalar_one()

    async def entry(self, session, key):
        return await session.get(DecisionEntry, key, populate_existing=True)

    async def selection(self, session, key):
        return (
            await session.execute(
                select(DecisionEntry, PipelineRun)
                .join(PipelineRun, PipelineRun.id == DecisionEntry.run_id)
                .join(Project, Project.id == DecisionEntry.project_id)
                .where(DecisionEntry.key == key, PipelineRun.state.not_in(FINAL_RUN_STATES))
            )
        ).first()
