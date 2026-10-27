from app.features.project_management.pipeline_runs.models import PipelineRun, RunResumeReceipt
from sqlalchemy import or_, select


class SddRepository:
    async def runs(self, session, project_id, spec_dir):
        # Link only recorded handoffs in this project; a similar slug is not provenance.
        origin = select(PipelineRun.sdd_snapshot["handoff_from"].as_string()).where(
            PipelineRun.project_id == project_id,
            PipelineRun.sdd_snapshot["spec_dir"].as_string() == spec_dir,
            PipelineRun.sdd_snapshot["handoff_from"].as_string().is_not(None),
        )
        return list(
            await session.scalars(
                select(PipelineRun)
                .where(
                    PipelineRun.project_id == project_id,
                    or_(
                        PipelineRun.sdd_snapshot["spec_dir"].as_string() == spec_dir,
                        PipelineRun.sdd_snapshot["handoff_from"].as_string() == spec_dir,
                        PipelineRun.sdd_snapshot["spec_dir"].as_string().in_(origin),
                        PipelineRun.sdd_snapshot["handoff_from"].as_string().in_(origin),
                    ),
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
