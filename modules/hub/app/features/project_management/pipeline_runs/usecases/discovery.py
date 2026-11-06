"""Discovery query and exact owner inspection, never execution or approval."""

import asyncio
from typing import Annotated

from app.features.project_management.pipeline_runs.discovery_repo import DecisionDiscoveryRepository
from app.features.project_management.pipeline_runs.discovery_service import decode_cursor, page_result
from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.sdd.answer_publication import retain_publications
from app.features.project_management.sdd.progress import authority_revocation, carry_decisions
from app.features.project_management.sdd.services import SddService
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends


class DecisionDiscoveryUseCase:
    def __init__(self, repo: Annotated[DecisionDiscoveryRepository, Depends()]):
        self.repo = repo

    async def list(self, project_id, kind, question_state, cursor, limit):
        filters = {
            "project_id": str(project_id) if project_id else None,
            "kind": kind,
            "question_state": question_state,
        }
        after = decode_cursor(cursor, filters)
        async with AsyncTransaction() as session:
            if project_id and not await ProjectRepository().get(session, project_id):
                raise ProjectError(404, "Project not found")
            rows = await self.repo.page(session, project_id, kind, question_state, after, limit)
            return page_result(rows, limit, filters)

    async def review(self, request, observer):
        runs, projects = PipelineRunRepository(), ProjectRepository()
        async with AsyncTransaction() as session:
            entry = await self.repo.entry(session, request.key)
            if not entry:
                raise ProjectError(404, "Decision is no longer available")
            run = await runs.get(session, entry.run_id)
            if not run or run.state in FINAL_RUN_STATES:
                raise ProjectError(404, "Decision owner is no longer available")
            if not entry.actionable:
                raise ProjectError(409, "Answer publication is pending; inspect the owner history")
            if entry.fingerprint != request.fingerprint:
                raise ProjectError(409, "Decision changed; review the current subject explicitly")
            project = await projects.get(session, run.project_id)
            if not project:
                raise ProjectError(404, "Project not found")
            if not run.sdd_snapshot:
                return PipelineRunRead.model_validate(run)
            if (run.sdd_snapshot or {}).get("provider") != "devkit-spec":
                raise ProjectError(409, "Unsupported native decision")
            if not project.enabled or (project.github_connector_id, project.github_repository) != (
                run.github_connector_id,
                run.github_repository,
            ):
                raise ProjectError(409, "Project binding changed or project is disabled")
            basis = (run.revision, run.epoch, project.revision, project.github_connector_id, project.github_repository)
            run_id, snapshot, previous = run.id, dict(run.sdd_snapshot), dict(run.sdd_progress or {})
            connector, repository, number = project.github_connector_id, project.github_repository, run.pull_number
        try:
            async with asyncio.timeout(30):
                pull = await observer.get_pull_request(connector, repository, number)
        except TimeoutError:
            raise ProjectError(504, "Decision inspection exceeded its read budget") from None
        if pull.get("state") != "open":
            raise ProjectError(409, "Pull request is no longer open")
        token = await observer.get_token(connector, "github")
        revocation = authority_revocation(previous, pull)
        evidence = await SddService().inspect(
            repository,
            snapshot["spec_dir"],
            pull,
            token,
            snapshot=snapshot,
            approved=bool(previous.get("approval")) and not revocation,
        )
        evidence["observed_at"] = get_current_utc_time().isoformat()
        carry_decisions(previous, evidence)
        # An inspection cannot erase a current grant or reopen a withdrawn grant.
        if "approval" in previous and not revocation:
            evidence["approval"] = previous["approval"]
        if revocation:
            evidence.pop("approval", None)
            evidence["approval_withheld"] = True
            evidence["integrated"] = False
        evidence["pr_draft"] = bool(pull.get("draft"))
        changed = False
        async with AsyncTransaction() as session:
            run = await runs.get(session, run_id, lock=True)
            if run is None:
                raise ProjectError(404, "Decision owner no longer exists")
            project = await projects.get(session, run.project_id, lock=True)
            if project is None:
                raise ProjectError(404, "Project no longer exists")
            if (
                run.state in FINAL_RUN_STATES
                or not project.enabled
                or basis
                != (run.revision, run.epoch, project.revision, project.github_connector_id, project.github_repository)
            ):
                raise ProjectError(409, "Owner changed during inspection; retry Review")
            await retain_publications(session, run.id, evidence)
            run.sdd_progress = evidence
            if revocation:
                run.state, run.pause_reason = "blocked", revocation
            run.revision += 1
            await session.flush()
            current = await self.repo.entry(session, request.key)
            changed = not current or current.fingerprint != request.fingerprint
            result = PipelineRunRead.model_validate(run)
        if revocation:
            raise ProjectError(409, revocation)
        if changed:
            # Commit the new inspection basis before reporting an obsolete selection.
            raise ProjectError(409, "Subject changed during inspection; refresh and explicitly Review again")
        return result
