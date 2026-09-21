import logging
from datetime import datetime, timedelta
from typing import Annotated

from app.features.configuration.system_configs.models import SystemConfig
from app.features.configuration.system_configs.repos import SystemConfigRepository
from app.features.notifications.notifier import Notifier
from app.features.project_management.github_webhooks.repos import GitHubWebhookRepository
from app.features.project_management.github_webhooks.usecases import GitHubWebhookUseCase
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.projects.models import Project
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends

logger = logging.getLogger(__name__)

HEARTBEAT_CONFIG = "dispatcher.heartbeat"
# The external trigger fires every minute; this long without a tick means it stopped, not that it is late.
TICK_STALE_AFTER = timedelta(minutes=10)
# A stopped trigger is reported from webhook arrivals, which can be frequent.
STALE_NOTICE_INTERVAL = timedelta(hours=1)
# A stop older than this is history by the time a channel could be told about it.
STOP_NOTICE_HORIZON = timedelta(hours=24)


def tick_status(last_tick_at: datetime | None, now: datetime) -> str:
    if last_tick_at is None:
        return "never"
    return "stale" if now - last_tick_at > TICK_STALE_AFTER else "ok"


def parse_instant(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _minutes(delta: timedelta) -> int:
    return int(delta.total_seconds() // 60)


class TickHousekeepingUseCase:
    """Work every dispatcher tick owes the operator, beside the schedules it runs.

    Nothing here may fail a tick: each step logs its own failure and the tick goes on.
    """

    def __init__(
        self,
        notifier: Annotated[Notifier, Depends()],
        lifecycle: Annotated[PipelineRunUseCase, Depends()],
        configs: Annotated[SystemConfigRepository, Depends()],
        runs: Annotated[PipelineRunRepository, Depends()],
        deliveries: Annotated[GitHubWebhookRepository, Depends()],
    ) -> None:
        self.notifier = notifier
        self.lifecycle = lifecycle
        self.configs = configs
        self.runs = runs
        self.deliveries = deliveries

    async def last_tick_at(self) -> datetime | None:
        async with AsyncTransaction() as session:
            heartbeat = await self.configs.get_by_name(session, HEARTBEAT_CONFIG)
            return parse_instant((heartbeat.data or {}).get("last_tick_at")) if heartbeat is not None else None

    async def record_tick(self) -> None:
        """Note that the trigger fired, and tell the operator when it had been silent."""
        try:
            now = get_current_utc_time()
            async with AsyncTransaction() as session:
                heartbeat = await self.configs.get_by_name(session, HEARTBEAT_CONFIG)
                previous = parse_instant((heartbeat.data or {}).get("last_tick_at")) if heartbeat is not None else None
                data = {"last_tick_at": now.isoformat()}
                if heartbeat is None:
                    session.add(SystemConfig(name=HEARTBEAT_CONFIG, data=data))
                else:
                    heartbeat.data = data
            if tick_status(previous, now) == "stale" and previous is not None:
                await self.notifier.send(
                    f"Auto Hub: the scheduler trigger fired again after {_minutes(now - previous)} minutes of silence. "
                    "No run advanced on a timer in between."
                )
        except Exception:
            logger.exception("Recording the dispatcher tick failed")

    async def report_stopped_trigger(self) -> None:
        """Called when other traffic arrives: a hub that still receives webhooks but no ticks is stuck silently."""
        try:
            now = get_current_utc_time()
            async with AsyncTransaction() as session:
                heartbeat = await self.configs.get_by_name(session, HEARTBEAT_CONFIG)
                if heartbeat is None:
                    return
                data = dict(heartbeat.data or {})
                last_tick = parse_instant(data.get("last_tick_at"))
                last_notice = parse_instant(data.get("stale_notice_at"))
                if tick_status(last_tick, now) != "stale" or last_tick is None:
                    return
                if last_notice is not None and now - last_notice < STALE_NOTICE_INTERVAL:
                    return
                heartbeat.data = {**data, "stale_notice_at": now.isoformat()}
            await self.notifier.send(
                f"Auto Hub: the scheduler trigger has not fired for {_minutes(now - last_tick)} minutes. "
                "Runs only advance on webhooks until it does; check the Cloud Scheduler job."
            )
        except Exception:
            logger.exception("Checking for a stopped scheduler trigger failed")

    async def after_dispatch(self) -> None:
        await self._sweep_webhooks()
        await self._announce_stops()

    async def _sweep_webhooks(self) -> None:
        try:
            webhooks = GitHubWebhookUseCase(self.deliveries, self.runs, self.lifecycle)
            for notice in await webhooks.sweep_stalled(get_current_utc_time()):
                await self.notifier.send(f"Auto Hub: {notice}")
        except Exception:
            logger.exception("Sweeping stalled GitHub webhook deliveries failed")

    async def _announce_stops(self) -> None:
        try:
            now = get_current_utc_time()
            async with AsyncTransaction() as session:
                stops = []
                for run in await self.runs.list_unannounced_stops(session, since=now - STOP_NOTICE_HORIZON):
                    project = await session.get(Project, run.project_id)
                    stops.append((run.id, run.revision, _stop_notice(run, project)))
            for run_id, revision, text in stops:
                deliveries = await self.notifier.send(text)
                # Undelivered stops stay unannounced, so a channel added or repaired later still hears of them.
                if any(delivery.error is None for delivery in deliveries):
                    async with AsyncTransaction() as session:
                        await self.runs.mark_stop_announced(session, run_id, revision)
        except Exception:
            logger.exception("Announcing stopped pipeline runs failed")


def _stop_notice(run: PipelineRun, project: Project | None) -> str:
    where = (project.github_repository or project.name) if project is not None else "unknown project"
    lines = [
        f"Auto Hub: run {run.state} - {where}#{run.pull_number}",
        run.pull_url,
    ]
    if run.pause_reason:
        lines.append(f"Reason: {run.pause_reason}")
    return "\n".join(lines)
