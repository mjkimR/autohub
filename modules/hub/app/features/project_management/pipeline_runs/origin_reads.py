"""Project retained origins without creating a session or inferring entry channels."""

from .origin_repos import RunOriginRepository
from .schemas import PipelineRunRead, RunOrigin


async def read_runs(session, runs) -> list[PipelineRunRead]:
    if not runs:
        return []
    by_id = {run.id: run for run in runs}
    origins: dict = {run_id: [] for run_id in by_id}
    repo = RunOriginRepository()
    for run_id, item_id, plan_id, project_id in await repo.work_items(session, list(by_id)):
        if by_id[run_id].project_id == project_id:
            origins[run_id].append(RunOrigin(kind="work_plan", id=item_id, work_plan_id=plan_id))
    for run_id, session_id, catalog_id, url in await repo.sessions(session, list(by_id)):
        origins[run_id].append(RunOrigin(kind="provider_session", id=session_id, catalog_id=catalog_id, url=url))
    for run_id, claim_id, project_id, unit, batch_id, batch_project in await repo.claims(session, list(by_id)):
        if by_id[run_id].project_id == project_id:
            origins[run_id].append(
                RunOrigin(
                    kind="native_sdd",
                    id=claim_id,
                    unit=unit,
                    batch_id=batch_id if batch_project == project_id else None,
                )
            )
    result = []
    for run in runs:
        refs = sorted(
            {(ref.kind, str(ref.id)): ref for ref in origins[run.id]}.values(), key=lambda ref: (ref.kind, str(ref.id))
        )
        categories = {ref.kind for ref in refs}
        if run.sdd_snapshot:
            categories.add("native_sdd")
        source = "multiple" if len(categories) > 1 else next(iter(categories), "unknown")
        result.append(
            PipelineRunRead.model_validate(run).model_copy(
                update={"enrollment_source": source, "related_origins": refs}
            )
        )
    return result


async def read_run(session, run) -> PipelineRunRead:
    return (await read_runs(session, [run]))[0]
