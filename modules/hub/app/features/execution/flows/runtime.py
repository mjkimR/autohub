"""Durable state transitions. No external I/O or transaction ownership here."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from autohub_sdk import ApprovalStep, InputRef, LiteralValue, ReleaseSpec, TaskRef, TaskStep

from .adapters import WorkerAction, WorkerResult
from .errors import FlowError
from .models import FlowAttempt, FlowRun
from .validation import definition, steps_for, validate


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def contract(run: FlowRun):
    release = ReleaseSpec.model_validate(run.snapshot["definition"])
    steps, result, output = steps_for(release, TaskRef(key=run.task_key, contract_version=run.task_version), run.inputs)
    return release, steps, result, output


def resolve(binding, run, rows):
    if isinstance(binding, LiteralValue):
        return binding.value
    assert isinstance(binding, InputRef)
    value = (
        run.inputs if binding.source == "run" else next(row.output for row in rows if row.step_key == binding.step_id)
    )
    for key in binding.path:
        if not isinstance(value, dict) or key not in value:
            raise FlowError(422, "input-reference", "input field reference is unavailable")
        value = value[key]
    return value


async def command_transition(session, repo, run: FlowRun, action: str, now):
    _, specs, _, _ = contract(run)
    rows = await repo.steps(session, run.id)
    row = rows[run.step_index] if run.step_index < len(rows) else None
    spec = specs[run.step_index] if row else None
    if action == "cancel" and run.status not in ("completed", "canceled", "canceling"):
        # An intent can have reached a worker even when its response was lost.
        attempts = await repo.attempts(session, run.id)
        outstanding = any(item.status in ("intent", "ready", "running", "observing") for item in attempts)
        run.status = "canceling" if outstanding else "canceled"
        run.next_action_at = now if outstanding else None
        if row is not None and not outstanding:
            row.status, row.deadline = "canceled", None
        return
    if row and row.status == "waiting" and run.status == "waiting" and isinstance(spec, ApprovalStep):
        if row.deadline is not None and utc(row.deadline) <= now:
            raise FlowError(409, "approval-expired", "approval deadline has expired")
        if action == "approve":
            row.status = "completed"
            row.deadline = None
            run.step_index += 1
        elif action == "revise":
            if spec.revise_to is None or row.rework_count >= spec.max_revisions:
                raise FlowError(409, "revision-limit", "declared rework budget exhausted")
            row.rework_count += 1
            target = next(index for index, item in enumerate(specs) if item.id == spec.revise_to)
            for item in rows[target:]:
                item.status, item.output, item.deadline = "queued", None, None
            run.step_index = target
        else:
            raise FlowError(409, "invalid-command", "command is not allowed in this state")
        run.status, run.error, run.next_action_at = "queued", None, now
        return
    if action == "resume" and row and run.status == "failed" and row.status == "failed" and isinstance(spec, TaskStep):
        if row.attempt_count >= spec.max_attempts:
            raise FlowError(409, "attempt-limit", "declared attempt budget exhausted")
        row.status, row.output = "queued", None
        run.status, run.error, run.next_action_at = "queued", None, now
        return
    raise FlowError(409, "invalid-command", "command is not allowed in this state")


class FlowRuntime:
    def __init__(self, repo):
        self.repo = repo

    async def plan(self, session, run: FlowRun, now) -> WorkerAction | None:
        release, specs, result_step, output_schema = contract(run)
        rows = await self.repo.steps(session, run.id)
        if run.status not in ("queued", "running", "waiting", "canceling"):
            return None
        await self.repo.bump(session, run, now)
        if run.step_index >= len(rows):
            output = next(row.output for row in rows if row.step_key == result_step)
            try:
                validate(output_schema, output)
                run.status, run.output, run.error = "completed", output, None
            except FlowError:
                run.status, run.error = "failed", "flow-output-invalid"
            run.next_action_at = None
            return None
        row, spec = rows[run.step_index], specs[run.step_index]
        if isinstance(spec, ApprovalStep):
            if row.deadline is None:
                row.deadline = now + timedelta(seconds=spec.deadline_seconds)
            if utc(row.deadline) <= now:
                run.status, run.error, row.status = "failed", "approval-deadline", "failed"
                run.next_action_at = None
            else:
                run.status, row.status, run.next_action_at = "waiting", "waiting", row.deadline
            return None
        attempts = [item for item in await self.repo.attempts(session, run.id) if item.step_id == row.id]
        existing = attempts[-1] if attempts else None
        if row.status == "queued":
            if row.attempt_count >= spec.max_attempts:
                run.status, run.error, row.status = "failed", "attempt-limit", "failed"
                run.next_action_at = None
                return None
            row.attempt_count += 1
            inputs = {}
            error = None
            try:
                inputs = {key: resolve(binding, run, rows) for key, binding in spec.inputs.items()}
                validate(definition(release, spec.task).input_schema, inputs)
            except FlowError as exc:
                error = exc.code
            existing = FlowAttempt(
                id=uuid4(),
                run_id=run.id,
                step_id=row.id,
                number=row.attempt_count,
                status="failed" if error else "intent",
                inputs=inputs,
                error=error,
            )
            session.add(existing)
            if error:
                row.status, run.status, run.error, run.next_action_at = "failed", "failed", error, None
                return None
            row.status, run.status, run.error = "running", "running", None
            operation = "submit"
        elif existing is not None:
            operation = "cancel" if run.status == "canceling" else "submit" if existing.status == "ready" else "inspect"
        else:
            raise RuntimeError("running flow step has no durable attempt")
        await session.flush()
        return WorkerAction(
            run.id,
            existing.id,
            run.revision,
            operation,
            spec.task,
            existing.inputs,
            run.snapshot["bindings"][f"{spec.task.key}@{spec.task.contract_version}"],
            run.snapshot["release_id"],
            run.snapshot["digest"],
        )

    async def apply(self, session, run, action: WorkerAction, result: WorkerResult, now):
        _, specs, _, _ = contract(run)
        rows = await self.repo.steps(session, run.id)
        row = rows[run.step_index]
        attempt = await session.get(FlowAttempt, action.attempt_id)
        await self.repo.bump(session, run, now)
        if run.status == "canceling":
            if result.status in ("canceled", "completed", "failed"):
                attempt.status = result.status
                attempt.output = result.output
                # Preserve that completion/failure preceded the worker's cancel acknowledgment.
                attempt.error = result.error
                row.status, run.status, run.next_action_at = "canceled", "canceled", None
            else:
                run.next_action_at = now + timedelta(seconds=5)
            return
        if result.status == "not_found":
            # Persist authoritative absence; subsequent dispatch reuses the same intent ID.
            attempt.status = "ready"
            row.status, run.status = "running", "running"
            run.error = None
            run.next_action_at = now
            return
        if result.status == "pending":
            attempt.status, run.status = "observing", "waiting"
            attempt.output, attempt.error = result.output, result.error
            run.error = result.error
            run.next_action_at = now + timedelta(seconds=5)
            return
        if result.status in ("failed", "canceled"):
            attempt.status, attempt.error = result.status, result.error or f"worker-{result.status}"
            attempt.output = result.output
            row.status, run.status, run.error, run.next_action_at = "failed", "failed", attempt.error, None
            return
        spec = specs[run.step_index]
        assert isinstance(spec, TaskStep)
        release = ReleaseSpec.model_validate(run.snapshot["definition"])
        try:
            validate(definition(release, spec.task).output_schema, result.output)
        except FlowError:
            attempt.status, attempt.error = "failed", "worker-output-invalid"
            row.status, run.status, run.error, run.next_action_at = "failed", "failed", attempt.error, None
            return
        attempt.status, attempt.output = "completed", result.output
        row.status, row.output = "completed", result.output
        run.step_index += 1
        run.status, run.error, run.next_action_at = "queued", None, now
