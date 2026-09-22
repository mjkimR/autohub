from datetime import datetime, timedelta

from app.features.execution.tasks.domains.maintenance.history import HistoryRetentionRepository
from app.features.project_management.github_webhooks.repos import GitHubWebhookRepository
from app.features.scheduling.schedule_jobs.repos import ScheduleJobRepository
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time

SUCCEEDED_JOB_RETENTION = timedelta(days=3)
FAILED_JOB_RETENTION = timedelta(days=7)
PIPELINE_RUN_RETENTION = timedelta(days=30)
WEBHOOK_DELIVERY_RETENTION = timedelta(days=90)
PRUNE_INTERVAL = timedelta(hours=1)


class HistoryRetentionUseCase:
    async def execute(self) -> None:
        now = get_current_utc_time()
        repo = HistoryRetentionRepository()
        async with AsyncTransaction() as session:
            checkpoint = await repo.lock_checkpoint(session)
            previous = (checkpoint.data or {}).get("pruned_at")
            if isinstance(previous, str) and now - datetime.fromisoformat(previous) < PRUNE_INTERVAL:
                return
            runs = await repo.delete_runs(session, before=now - PIPELINE_RUN_RETENTION, now=now)
            jobs = await ScheduleJobRepository().delete_history(
                session,
                succeeded_before=now - SUCCEEDED_JOB_RETENTION,
                failed_before=now - FAILED_JOB_RETENTION,
            )
            await GitHubWebhookRepository().delete_received_before(session, now - WEBHOOK_DELIVERY_RETENTION)
            # A failed deletion rolls this back too; another tick can retry without waiting an hour.
            checkpoint.data = {"pruned_at": now.isoformat(), "deleted_runs": runs, "deleted_jobs": jobs}
