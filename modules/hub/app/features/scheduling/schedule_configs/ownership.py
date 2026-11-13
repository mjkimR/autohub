"""Shared task classification; ownership does not grant mutation authority."""

from typing import Literal

OwnerKind = Literal[
    "system_maintenance",
    "project_dispatch",
    "connection_test",
    "project_agent_schedule",
    "project_observation",
    "operator",
]
RESERVED: dict[str, OwnerKind] = {
    "system.maintain": "system_maintenance",
    "pipeline.dispatch_project": "project_dispatch",
    "pipeline.connection_test": "connection_test",
}


def owner_kind(task: str, agent_owned: bool = False) -> OwnerKind:
    if task in RESERVED:
        return RESERVED[task]
    if agent_owned:
        return "project_agent_schedule"
    return "project_observation" if task == "pipeline.observe_project" else "operator"


def mutation_allowed(kind: OwnerKind) -> bool:
    return kind in {"operator", "project_observation"}
