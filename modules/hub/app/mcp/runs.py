from app.features.project_management.pipeline_runs.interaction_schemas import ResumeRunRequest
from app.features.project_management.pipeline_runs.schemas import PauseRunRequest
from app.mcp.auth import authenticated_context
from app.mcp.contracts import (
    AttemptFilter,
    AttemptList,
    AttemptView,
    Enroll,
    Items,
    Pause,
    Resume,
    RunFilter,
    RunId,
    RunView,
    RunWait,
)
from app.mcp.dependencies import Dependencies
from app.mcp.names import catalog_keys
from app.mcp.registration import register
from app.mcp.waiting import wait_for_change
from app_mcp import ToolRegistry


def register_runs(registry: ToolRegistry, deps: Dependencies) -> None:
    async def view(row, keys: dict | None = None) -> RunView:
        keys = keys if keys is not None else await catalog_keys(deps)
        return RunView.model_validate(row).model_copy(update={"catalog_key": keys.get(row.ai_catalog_id)})

    async def list_runs(args: RunFilter) -> Items[RunView]:
        result = await deps.queries.list_runs(
            args.project_id, args.offset, args.limit, args.state, args.search, args.pull_number, args.group_key
        )
        keys = await catalog_keys(deps)
        return Items(items=[await view(row, keys) for row in result.items], total_count=result.total_count)

    async def get_run(args: RunWait) -> RunView:
        keys = await catalog_keys(deps)

        async def read() -> RunView:
            return await view(await deps.queries.get(args.run_id), keys)

        return await wait_for_change(
            read, lambda run: (run.state, run.revision), lambda run: run.settled, args.wait_seconds
        )

    async def enroll(args: Enroll) -> RunView:
        return await view(await deps.runs.enroll(args.project_id, args.pull_request))

    async def attempts(args: AttemptFilter) -> AttemptList:
        result = await deps.queries.list_attempts(args.run_id, offset=args.offset, limit=args.limit)
        return AttemptList(
            items=[AttemptView.model_validate(row) for row in result.items],
            total_count=result.total_count,
            summary=result.summary,
        )

    async def pause(args: Pause) -> RunView:
        return await view(await deps.runs.pause_run(args.run_id, PauseRunRequest(reason=args.reason)))

    async def resume(args: Resume) -> RunView:
        return await view(
            await deps.runs.resume_run(
                args.run_id,
                request=ResumeRunRequest(**args.model_dump(exclude={"run_id"})),
                actor=f"machine:{(await authenticated_context()).subject}",
            )
        )

    async def cancel(args: RunId) -> RunView:
        return await view(await deps.runs.cancel_run(args.run_id))

    register(
        registry,
        "runs_list",
        "List runs, including prior enrollment after a lost response; filter by pull_number for one pull request. Results omit PR bodies and worker state.",
        RunFilter,
        Items[RunView],
        list_runs,
    )
    register(
        registry,
        "runs_get",
        "Read current run state and PR link. Set wait_seconds to wait for the next state change; background work continues after disconnect.",
        RunWait,
        RunView,
        get_run,
    )
    register(
        registry,
        "runs_enroll",
        "Register an existing open PR for background execution. Does not create a PR. Explicitly set implemented=true for completed code or false to request implementation; omission is rejected. Existing project automation and merge policies apply. Active duplicates conflict; use runs_list with project_id and pull_number to recover after a lost response.",
        Enroll,
        RunView,
        enroll,
        write=True,
    )
    register(
        registry,
        "runs_attempts",
        "Read bounded attempt outcomes, failure details and conversation links without request snapshots.",
        AttemptFilter,
        AttemptList,
        attempts,
    )
    register(
        registry,
        "runs_pause",
        "Pause a run and release its lease; already delivered external work may continue.",
        Pause,
        RunView,
        pause,
        write=True,
    )
    register(
        registry,
        "runs_resume",
        "Resume a paused or blocked run after inspecting its cause and PR. Pass request_id and the inspected expected_revision, plus answer_id for a pending decision. This may request agent work. Retry identical input with the same request_id after response loss; the receipt returns current state without creating another attempt.",
        Resume,
        RunView,
        resume,
        write=True,
    )
    register(
        registry,
        "runs_cancel",
        "Cancel Hub progression for a run. Already delivered external work may continue.",
        RunId,
        RunView,
        cancel,
        write=True,
    )
