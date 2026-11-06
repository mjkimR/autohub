"""Transaction boundaries for immutable selection and future-admission controls."""

from typing import Annotated

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends

from .batch_models import SddBatch, SddBatchControl, SddBatchMember
from .batch_policy import ordered_selection, project_basis, same_request
from .batch_repo import BatchRepository
from .usecases import SddUseCase


class SddBatchUseCase:
    def __init__(self, projects: Annotated[ProjectService, Depends()], sdd: Annotated[SddUseCase, Depends()]):
        self.projects, self.sdd, self.repo = projects, sdd, BatchRepository()

    async def _read(self, session, row):
        return {
            "id": str(row.id),
            "project_id": str(row.project_id),
            "state": row.state,
            "revision": row.revision,
            "exclusion": row.exclusion,
            "detail": row.detail,
            "basis": row.basis,
            "evaluation": row.evaluation,
            "members": [
                {
                    "id": str(m.id),
                    "anchor_id": m.anchor_id,
                    "path": m.path,
                    "position": m.position,
                    "initial": m.initial,
                    "phase": m.phase,
                    "state": m.state,
                    "spec_anchor": m.spec_anchor,
                    "outcome": m.outcome,
                    "claims": [
                        {
                            "id": str(c.id),
                            "activity": c.activity,
                            "settled": c.settled,
                            "branch": c.checkpoint.get("branch"),
                            "initial_sha": c.checkpoint.get("initial_sha"),
                            "pull_number": c.checkpoint.get("pull_number"),
                            "run_id": str(c.run_id) if c.run_id else c.checkpoint.get("run_id"),
                        }
                        for c in await self.repo.claims(session, m.id)
                    ],
                }
                for m in await self.repo.members(session, row.id)
            ],
        }

    async def get(self, project_id, batch_id):
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id)
            row = await self.repo.get(session, project_id, batch_id)
            if row is None:
                raise ProjectError(404, "SDD batch not found")
            return await self._read(session, row)

    async def lists(self, project_id):
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id)
            return [await self._read(session, row) for row in await self.repo.lists(session, project_id)]

    async def create(self, project_id, request, actor):
        from .milestones import preview_milestone
        from .repos import SddRepository

        digest = request_digest(request.model_dump(mode="json"))
        async with AsyncTransaction() as session:
            project = await self.projects.get(session, project_id)
            previous = await self.repo.request(session, project_id, request.request_id)
            if previous:
                same_request(previous, actor, digest)
                return await self._read(session, previous)
        project = await self.sdd.milestone_context(project_id)
        identity = project_basis(project)

        async def runs_for(unit):
            async with AsyncTransaction() as session:
                return await SddRepository().runs(session, project_id, unit)

        preview = await preview_milestone(self.sdd.observer, project, request, runs_for, capture=True)
        if preview["resolved_sha"] != request.expected_sha:
            raise ProjectError(409, "Preview SHA changed; inspect a fresh selection")
        ordered = ordered_selection(preview, [m.model_dump(mode="json") for m in request.members])
        async with AsyncTransaction() as session:
            current = await self.projects.get(session, project_id, lock=True)
            previous = await self.repo.request(session, project_id, request.request_id)
            if previous:
                same_request(previous, actor, digest)
                return await self._read(session, previous)
            if project_basis(current) != identity:
                raise ProjectError(409, "Project changed while selection was evaluated")
            if await self.repo.active(session, project_id):
                raise ProjectError(409, "An unsettled batch already excludes another selection")
            from .batch_evidence import remote_head

            if await remote_head(self.sdd.observer, current, request.ref) != preview["resolved_sha"]:
                raise ProjectError(409, "Selected base moved before batch creation committed")
            basis = {
                "project": identity,
                "ref": request.ref,
                "sha": request.expected_sha,
                "milestone": preview["milestone"],
                "through_development": True,
                "evidence": preview["batch_basis"],
                "edges": preview["edges"],
            }
            row = await self.repo.save(
                session,
                SddBatch(
                    project_id=project_id,
                    request_id=request.request_id,
                    request_digest=digest,
                    actor=actor,
                    basis=basis,
                    evaluation={"observed_at": preview["observed_at"]},
                ),
            )
            for position, member in enumerate(ordered):
                prefs = member["preferences"]
                member["effective_preferences"] = {
                    "planning_effort": prefs.get("planning_effort") or member.get("planning_effort") or "medium",
                    "dev_effort": prefs.get("dev_effort") or member.get("dev_effort") or "medium",
                    "planning_catalog": prefs.get("planning_catalog")
                    or preview.get("default_catalog")
                    or "personal-codex",
                    "dev_catalog": prefs.get("dev_catalog") or preview.get("default_catalog") or "personal-codex",
                }
                await self.repo.save(
                    session,
                    SddBatchMember(
                        batch_id=row.id,
                        position=position,
                        anchor_id=member["id"],
                        path=member["path"],
                        initial=member,
                        phase=member["activity_kind"],
                    ),
                )
            return await self._read(session, row)

    async def control(self, project_id, batch_id, request, actor):
        digest = request_digest(request.model_dump(mode="json"))
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id, lock=True)
            row = await self.repo.get(session, project_id, batch_id, lock=True)
            if row is None:
                raise ProjectError(404, "SDD batch not found")
            previous = await self.repo.receipt(session, batch_id, request.request_id)
            if previous:
                same_request(previous, actor, digest)
                return await self._read(session, row)
            if row.revision != request.expected_revision:
                raise ProjectError(409, "Batch revision changed; review current future-admission state")
            if row.state in ("stopped", "completed"):
                raise ProjectError(409, "Future admission is terminal")
            row.state = {"pause": "paused", "resume": "running", "stop": "stopped"}[request.action]
            row.revision += 1
            if request.action == "resume":
                members = await self.repo.members(session, row.id)
                refusals = [
                    c for m in members for c in await self.repo.claims(session, m.id) if c.checkpoint.get("refusal")
                ]
                if refusals:
                    row.evaluation = {**row.evaluation, "reviewed_refusal": str(refusals[-1].id)}
            if request.action == "stop":
                members = await self.repo.members(session, row.id)
                all_claims = [c for m in members for c in await self.repo.claims(session, m.id)]
                unsettled = any(not c.settled for c in all_claims)
                if not unsettled:
                    row.exclusion = False
            await self.repo.save(
                session,
                SddBatchControl(
                    batch_id=batch_id,
                    request_id=request.request_id,
                    actor=actor,
                    request_digest=digest,
                    action=request.action,
                ),
            )
            return await self._read(session, row)
