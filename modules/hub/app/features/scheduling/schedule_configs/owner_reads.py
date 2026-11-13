"""Assemble owner facts from bounded repository lookups in the caller's session."""

from uuid import UUID

from .owner_repos import ScheduleOwnerRepository
from .ownership import mutation_allowed, owner_kind
from .schemas import ScheduleConfigRead, ScheduleOwner


def payload_uuid(payload, key):
    value = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(value, str):
        return None
    try:
        parsed = UUID(value)
        return parsed if value.lower() in {str(parsed), parsed.hex} else None
    except ValueError:
        return None


class ScheduleOwnerService:
    async def read(self, session, rows):
        if not rows:
            return []
        repo = ScheduleOwnerRepository()
        agents = {row.schedule_config_id: row for row in await repo.agents(session, [row.id for row in rows])}
        test_ids = {
            value
            for row in rows
            if row.task_func == "pipeline.connection_test" and (value := payload_uuid(row.payload, "test_id"))
        }
        tests = {row.id: row for row in await repo.tests(session, test_ids)}
        project_ids = {row.project_id for row in [*agents.values(), *tests.values()]}
        project_ids.update(value for row in rows if (value := payload_uuid(row.payload, "project_id")))
        projects = await repo.projects(session, project_ids)
        result = []
        for row in rows:
            agent = agents.get(row.id)
            kind = owner_kind(row.task_func, agent is not None)
            project_id = object_id = None
            if kind in {"project_dispatch", "project_observation"}:
                candidate = payload_uuid(row.payload, "project_id")
                if candidate in projects:
                    project_id = object_id = candidate
            elif kind == "connection_test":
                test = tests.get(payload_uuid(row.payload, "test_id"))
                if test:
                    object_id = test.id
                    project_id = test.project_id if test.project_id in projects else None
            elif kind == "project_agent_schedule" and agent:
                object_id = agent.id
                project_id = agent.project_id if agent.project_id in projects else None
            result.append(
                ScheduleConfigRead.model_validate(row).model_copy(
                    update={
                        "owner": ScheduleOwner(kind=kind, project_id=project_id, object_id=object_id),
                        "generic_mutation_allowed": mutation_allowed(kind),
                    }
                )
            )
        return result
