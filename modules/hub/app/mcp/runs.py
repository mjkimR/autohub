from app.features.project_management.pipeline_runs.schemas import PauseRunRequest
from app.mcp.contracts import AttemptFilter, AttemptList, AttemptView, Enroll, Items, Pause, RunFilter, RunId, RunView
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app_mcp import ToolRegistry


def register_runs(registry: ToolRegistry, deps: Dependencies) -> None:
    async def list_runs(args: RunFilter) -> Items[RunView]:
        result = await deps.queries.list_runs(args.project_id, args.offset, args.limit, args.state, args.search)
        return Items(items=[RunView.model_validate(row) for row in result.items], total_count=result.total_count)

    async def get_run(args: RunId) -> RunView:
        return RunView.model_validate(await deps.queries.get(args.run_id))

    async def enroll(args: Enroll) -> RunView:
        return RunView.model_validate(await deps.runs.enroll(args.project_id, args.pull_request))

    async def attempts(args: AttemptFilter) -> AttemptList:
        result = await deps.queries.list_attempts(args.run_id, offset=args.offset, limit=args.limit)
        return AttemptList(
            items=[AttemptView.model_validate(row) for row in result.items],
            total_count=result.total_count,
            summary=result.summary,
        )

    async def pause(args: Pause) -> RunView:
        return RunView.model_validate(await deps.runs.pause_run(args.run_id, PauseRunRequest(reason=args.reason)))

    async def resume(args: RunId) -> RunView:
        return RunView.model_validate(await deps.runs.resume_run(args.run_id))

    async def cancel(args: RunId) -> RunView:
        return RunView.model_validate(await deps.runs.cancel_run(args.run_id))

    register(
        registry,
        "runs.list",
        "List runs, including prior enrollment after a lost response. Results omit PR bodies and worker state.",
        RunFilter,
        Items[RunView],
        list_runs,
    )
    register(
        registry,
        "runs.get",
        "Read current run state and PR link. Background work continues after disconnect; query again when needed.",
        RunId,
        RunView,
        get_run,
    )
    register(
        registry,
        "runs.enroll",
        "Register an existing open PR for background execution. Does not create a PR. Set implemented when code is already complete. Active duplicates conflict; use runs.list to recover.",
        Enroll,
        RunView,
        enroll,
        write=True,
    )
    register(
        registry,
        "runs.attempts",
        "Read bounded attempt outcomes, failure details and conversation links without request snapshots.",
        AttemptFilter,
        AttemptList,
        attempts,
    )
    register(
        registry,
        "runs.pause",
        "Pause a run and release its lease; already delivered external work may continue.",
        Pause,
        RunView,
        pause,
        write=True,
    )
    register(
        registry,
        "runs.resume",
        "Resume a paused or blocked run after reconciling its PR. May resume agent work; after a lost response read status before retrying.",
        RunId,
        RunView,
        resume,
        write=True,
    )
    register(
        registry,
        "runs.cancel",
        "Cancel Hub progression for a run. Already delivered external work may continue.",
        RunId,
        RunView,
        cancel,
        write=True,
    )
