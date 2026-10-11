from app.features.project_management.pipeline_runs.models import RunResumeReceipt
from sqlalchemy import select


class SpecrigRepository:
    async def decisions(self, session, run_id):
        return list(
            await session.scalars(
                select(RunResumeReceipt)
                .where(
                    RunResumeReceipt.pipeline_run_id == run_id,
                    RunResumeReceipt.decision_evidence.is_not(None),
                )
                .order_by(RunResumeReceipt.created_at.desc(), RunResumeReceipt.id.desc())
                .limit(100)
            )
        )
