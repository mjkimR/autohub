from copy import deepcopy
from typing import Annotated
from uuid import UUID, uuid4

from app_layer_base.utils.time_util import get_current_utc_time
from app_prebuilt_auth.api_key.schemas import MachinePrincipal
from autohub_sdk import (
    ActivationReceipt,
    AttemptView,
    ReleaseReceipt,
    ReleaseSpec,
    RunCommand,
    RunRequest,
    RunView,
    TaskRef,
)
from fastapi import Depends

from .adapters import WorkerBindings, get_worker_bindings
from .auth import FLOW_APPROVE, FLOW_READ, FLOW_WRITE, require_scope
from .errors import FlowError
from .models import FlowCommand, FlowEnvironment, FlowRelease, FlowRun, FlowStep
from .repos import FlowRepository
from .validation import check_ref, check_release, definition, digest, steps_for, validate


class FlowService:
    def __init__(
        self,
        repo: Annotated[FlowRepository, Depends()],
        bindings: Annotated[WorkerBindings, Depends(get_worker_bindings)],
    ):
        self.repo, self.bindings = repo, bindings

    async def owned(self, session, provider, environment, principal, *, lock=False):
        row = await self.repo.environment(session, provider, environment, lock=lock)
        if row is None:
            raise FlowError(404, "environment-not-found", "provider environment is not registered")
        if row.owner_machine_id != principal.machine_id:
            raise FlowError(403, "environment-owner", "machine does not own this provider environment")
        return row

    async def register(self, session, provider, environment, release_id, data: ReleaseSpec, principal):
        require_scope(principal, FLOW_WRITE)
        await self.repo.insert_once(
            session,
            FlowEnvironment,
            {"provider": provider, "environment": environment, "owner_machine_id": principal.machine_id, "revision": 0},
        )
        await self.owned(session, provider, environment, principal, lock=True)
        prior = await self.repo.release(session, provider, environment, release_id)
        request_digest = digest(data.model_dump(mode="python"))
        if prior is not None:
            if prior.digest != request_digest:
                raise FlowError(409, "release-conflict", "release ID already has different contents")
            return self.receipt(prior)
        check_release(data)
        resolved = self.bindings.resolve(data)
        await self.repo.insert_once(
            session,
            FlowRelease,
            {
                "id": uuid4(),
                "provider": provider,
                "environment": environment,
                "release_id": release_id,
                "digest": request_digest,
                "definition": data.model_dump(mode="json"),
                "bindings": resolved,
            },
        )
        row = await self.repo.release(session, provider, environment, release_id)
        if row.digest != request_digest:
            raise FlowError(409, "release-conflict", "release ID already has different contents")
        return self.receipt(row)

    @staticmethod
    def receipt(row):
        return ReleaseReceipt(
            provider=row.provider, environment=row.environment, release_id=row.release_id, digest=row.digest
        )

    async def activate(self, session, provider, environment, release_id, expected, principal):
        require_scope(principal, FLOW_WRITE)
        owner = await self.owned(session, provider, environment, principal, lock=True)
        release = await self.repo.release(session, provider, environment, release_id)
        if release is None:
            raise FlowError(404, "release-not-found", "register the release first")
        revision = await self.repo.activate(session, owner, release_id, expected, get_current_utc_time())
        return ActivationReceipt(**self.receipt(release).model_dump(), revision=revision)

    async def start(self, session, data: RunRequest, principal):
        require_scope(principal, FLOW_WRITE)
        if len(data.provider) > 64 or len(data.environment) > 64:
            raise FlowError(422, "contract-limit", "provider or environment exceeds host limits")
        check_ref(data.task)
        owner = await self.owned(session, data.provider, data.environment, principal, lock=True)
        request_digest = digest(data.model_dump(mode="python"))
        existing = await self.repo.request(session, data.provider, data.environment, data.idempotency_key)
        if existing:
            if existing.request_digest != request_digest:
                raise FlowError(409, "request-conflict", "request key already has different contents")
            return await self.read(session, existing)
        if owner.active_release_id is None:
            raise FlowError(409, "no-active-release", "activate a release first")
        release = await self.repo.release(session, data.provider, data.environment, owner.active_release_id)
        spec = ReleaseSpec.model_validate(release.definition)
        item = definition(spec, data.task)
        validate(item.input_schema, data.inputs)
        run_id = uuid4()
        await self.repo.insert_once(
            session,
            FlowRun,
            {
                "id": run_id,
                "provider": data.provider,
                "environment": data.environment,
                "release_pk": release.id,
                "request_key": data.idempotency_key,
                "request_digest": request_digest,
                "task_key": data.task.key,
                "task_version": data.task.contract_version,
                "inputs": deepcopy(data.inputs),
                "snapshot": {
                    "release_id": release.release_id,
                    "digest": release.digest,
                    "definition": deepcopy(release.definition),
                    "bindings": deepcopy(release.bindings),
                },
                "status": "queued",
                "revision": 0,
                "step_index": 0,
            },
        )
        row = await self.repo.request(session, data.provider, data.environment, data.idempotency_key)
        if row.request_digest != request_digest:
            raise FlowError(409, "request-conflict", "request key already has different contents")
        if row.id == run_id:
            steps, _, _ = steps_for(spec, data.task, data.inputs)
            for index, step in enumerate(steps):
                session.add(FlowStep(id=uuid4(), run_id=run_id, step_key=step.id, position=index, status="queued"))
            await session.flush()
        return await self.read(session, row)

    async def read(self, session, run: FlowRun) -> RunView:
        steps = await self.repo.steps(session, run.id)
        step_by_id = {step.id: step.step_key for step in steps}
        attempts = await self.repo.attempts(session, run.id)
        current = steps[run.step_index] if run.step_index < len(steps) else None
        reason = None
        if run.status == "waiting":
            reason = "approval" if current and current.status == "waiting" else "external-result"
        return RunView.model_validate(
            dict(
                run_id=str(run.id),
                provider=run.provider,
                environment=run.environment,
                release_id=run.snapshot["release_id"],
                release_digest=run.snapshot["digest"],
                task=TaskRef(key=run.task_key, contract_version=run.task_version),
                revision=run.revision,
                status=run.status,
                current_step=current.step_key if current and run.status not in ("completed", "canceled") else None,
                waiting_reason=reason,
                attempts=tuple(
                    AttemptView(
                        step_id=step_by_id[item.step_id],
                        number=item.number,
                        status="running" if item.status in ("intent", "ready") else item.status,
                        inputs=item.inputs,
                        output=item.output,
                        error=item.error,
                    )
                    for item in attempts
                ),
                output=run.output,
                error=run.error,
            )
        )

    async def get(self, session, run_id, principal, *, write=False):
        require_scope(principal, FLOW_WRITE if write else FLOW_READ)
        run = await self.repo.run(session, run_id, lock=write)
        if run is None:
            raise FlowError(404, "run-not-found", "unknown run ID")
        await self.owned(session, run.provider, run.environment, principal)
        return run

    async def command(self, session, run_id: UUID, data: RunCommand, principal: MachinePrincipal):
        run = await self.get(session, run_id, principal, write=True)
        if data.action in ("approve", "revise"):
            require_scope(principal, FLOW_APPROVE)
        request_digest = digest(data.model_dump(mode="python"))
        prior = await self.repo.command(session, run_id, data.command_id)
        if prior:
            if prior.digest != request_digest:
                raise FlowError(409, "command-conflict", "command ID already has different contents")
            return RunView.model_validate(prior.receipt)
        if run.revision != data.expected_revision:
            raise FlowError(409, "stale-revision", "run revision changed")
        from .runtime import command_transition

        now = get_current_utc_time()
        await self.repo.bump(session, run, now)
        await command_transition(session, self.repo, run, data.action, now)
        await session.flush()
        receipt = await self.read(session, run)
        session.add(
            FlowCommand(
                id=uuid4(),
                run_id=run.id,
                command_key=data.command_id,
                digest=request_digest,
                actor=f"machine:{principal.machine_id}:key:{principal.key_id}",
                receipt=receipt.model_dump(mode="json"),
            )
        )
        return receipt
