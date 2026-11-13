"""Settle finished optimistic activity reservations without advancing repository work."""

from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService
from app.features.project_management.sdd.activity_claims import settle_individual_claims


async def settle_activity_history():
    await settle_individual_claims(ProjectService(ProjectRepository()))
