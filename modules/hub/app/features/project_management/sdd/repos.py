from app.features.project_management.pipeline_runs.models import PipelineRun, RunResumeReceipt
from sqlalchemy import select


class SddRepository:
    async def runs(self, session, project_id, spec_dir):
        return list(
            await session.scalars(
                select(PipelineRun)
                .where(
                    PipelineRun.project_id == project_id,
                    PipelineRun.sdd_snapshot["spec_dir"].as_string() == spec_dir,
                )
                .order_by(PipelineRun.created_at.desc(), PipelineRun.id.desc())
                .limit(20)
            )
        )

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
