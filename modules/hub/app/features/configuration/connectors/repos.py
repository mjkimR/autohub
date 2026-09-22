from uuid import UUID

from app.features.configuration.connectors.models import Connector
from app.features.configuration.connectors.schemas import ConnectorCreate, ConnectorPatch, ConnectorPut
from app.features.project_management.connection_tests.models import ACTIVE, ConnectionTest
from app_layer_base.base.repos.base import BaseRepository
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class ConnectorRepository(BaseRepository[Connector, ConnectorCreate, ConnectorPut, ConnectorPatch]):
    model = Connector

    async def lock(self, session: AsyncSession, connector_id: UUID) -> Connector | None:
        return await session.scalar(
            select(Connector)
            .where(Connector.id == connector_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def has_unfinished_connection_tests(self, session: AsyncSession, connector_id: UUID) -> bool:
        return (
            await session.scalar(
                select(ConnectionTest.id)
                .where(
                    or_(
                        ConnectionTest.connector_id == connector_id,
                        ConnectionTest.catalog_snapshot["connector_id"].as_string() == str(connector_id),
                    ),
                    or_(ConnectionTest.status == ACTIVE, ConnectionTest.cleanup_status != "completed"),
                )
                .limit(1)
            )
            is not None
        )
