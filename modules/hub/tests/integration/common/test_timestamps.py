"""Hub metadata and real configuration owner timestamp contracts."""
from datetime import UTC, datetime

import pytest
from app.features.configuration.system_configs.models import SystemConfig
from app.features.configuration.system_configs.repos import SystemConfigRepository
from app.features.configuration.system_configs.schemas import SystemConfigPatch
from app.features.configuration.system_configs.services import SystemConfigService
from app_layer_base.base.models.mixin import Base

pytestmark = pytest.mark.integration
OLD = datetime(2000, 1, 1, tzinfo=UTC)


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def test_all_hub_timestamp_models_have_update_policy(app):
    models = [m.class_ for m in Base.registry.mappers if m.class_.__module__.startswith('app.') and 'updated_at' in m.columns]
    assert len(models) >= 47
    assert all(model.__table__.c.updated_at.onupdate is not None for model in models)


async def test_configuration_service_advances_updated_at_without_changing_created_at(session):
    row = SystemConfig(name='timestamp-test', data={}, created_at=OLD, updated_at=OLD)
    session.add(row)
    await session.flush()
    await SystemConfigService(SystemConfigRepository()).patch(session, row.id, SystemConfigPatch(data={'changed': True}))
    await session.refresh(row)
    assert utc(row.updated_at) > OLD
    assert utc(row.created_at) == OLD
