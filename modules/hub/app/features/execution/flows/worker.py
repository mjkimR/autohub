"""Short DB transactions around worker I/O, with durable intents and fenced results."""

from uuid import UUID, uuid4

from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time

from .adapters import RECOVERABLE_ERRORS, RETIRED_BRIDGE, WorkerAdapter, WorkerResult, retired_binding
from .repos import FlowRepository
from .runtime import FlowRuntime, retire_undispatched, uses_retired_bridge


class FlowWorker:
    def __init__(self, adapter: WorkerAdapter | None = None, session_maker=None):
        self.repo = FlowRepository()
        self.runtime = FlowRuntime(self.repo)
        self.adapter = adapter or WorkerAdapter()
        self.session_maker = session_maker

    def transaction(self):
        return AsyncTransaction(session_maker=self.session_maker)

    async def advance(self, run_id: UUID) -> bool:
        token = uuid4()
        async with self.transaction() as session:
            run = await self.repo.run(session, run_id, lock=True)
            if run is None:
                return False
            if await retire_undispatched(session, self.repo, run, get_current_utc_time()):
                return True
            if not await self.repo.claim(session, run_id, token, get_current_utc_time()):
                return False
        try:
            async with self.transaction() as session:
                run = await self.repo.fenced(session, run_id, token, get_current_utc_time())
                if run is None:
                    return False
                retired = uses_retired_bridge(run)
                action = await self.runtime.plan(session, run, get_current_utc_time())
            if action is None:
                return True
            # A recovered intent is inspected first. Only authoritative absence can
            # resubmit the SAME ID. Native identity is pure and can be recomputed.
            result = None
            error = None
            try:
                if retired:
                    if retired_binding(action.binding):
                        from .bridge import PRBridgeWorker

                        result = await PRBridgeWorker().execute(action)
                    else:
                        result = WorkerResult(attempt_id=action.attempt_id, status="failed", error=RETIRED_BRIDGE)
                else:
                    result = await self.adapter.execute(action)
            except RECOVERABLE_ERRORS:
                error = "worker-unavailable"
            async with self.transaction() as session:
                now = get_current_utc_time()
                run = await self.repo.fenced(session, run_id, token, now)
                if run is None or run.revision != action.revision:
                    return False
                if error:
                    from datetime import timedelta

                    await self.repo.bump(session, run, now)
                    run.error = error
                    if run.status != "canceling":
                        run.status = "waiting"
                    run.next_action_at = now + timedelta(seconds=5)
                elif result is not None:
                    await self.runtime.apply(session, run, action, result, now)
            return True
        finally:
            async with self.transaction() as session:
                await self.repo.release_lease(session, run_id, token)

    async def tick(self, *, limit=32) -> None:
        async with self.transaction() as session:
            pending = await self.repo.ready(session, get_current_utc_time(), limit)
        # Serial per batch, no process-global locks; separate ticks can compete safely.
        failures = 0
        for run_id in pending:
            try:
                await self.advance(run_id)
            except Exception:
                from app_layer_base.core.log import logger

                failures += 1
                logger.exception("SDK flow advancement failed")
        if failures:
            raise RuntimeError(f"{failures} SDK flow advances failed; remaining work will retry")
