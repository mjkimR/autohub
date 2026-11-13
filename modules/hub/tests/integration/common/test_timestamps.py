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
    models = [
        m.class_ for m in Base.registry.mappers if m.class_.__module__.startswith("app.") and "updated_at" in m.columns
    ]
    assert len(models) >= 47
    assert all(model.__table__.c.updated_at.onupdate is not None for model in models)


async def test_configuration_service_advances_updated_at_without_changing_created_at(session):
    row = SystemConfig(name="timestamp-test", data={}, created_at=OLD, updated_at=OLD)
    session.add(row)
    await session.flush()
    await SystemConfigService(SystemConfigRepository()).patch(
        session, row.id, SystemConfigPatch(data={"changed": True})
    )
    await session.refresh(row)
    assert utc(row.updated_at) > OLD
    assert utc(row.created_at) == OLD


@pytest.fixture
def clock(monkeypatch):
    from types import SimpleNamespace

    from app_layer_base.utils import time_util

    current = [datetime(2030, 1, 1, tzinfo=UTC)]

    class ControlledDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return current[0].astimezone(tz)

    monkeypatch.setattr(time_util, "datetime", SimpleNamespace(datetime=ControlledDateTime))
    return current


async def test_service_clock_noop_rejected_write_and_historical_read(session, clock):
    row = SystemConfig(name="clock-owner", data={}, created_at=OLD, updated_at=OLD)
    other = SystemConfig(name="occupied-name", data={})
    session.add_all([row, other])
    await session.flush()
    await session.refresh(row)
    assert utc(row.updated_at) == OLD
    row.data = {}
    await session.flush()
    assert utc(row.updated_at) == OLD
    service = SystemConfigService(SystemConfigRepository())
    with pytest.raises(Exception) as exc:
        await service.patch(session, row.id, SystemConfigPatch(name=other.name))
    assert "unique" in str(exc.value).lower()
    await session.refresh(row)
    assert utc(row.updated_at) == OLD
    await service.patch(session, row.id, SystemConfigPatch(data={"saved": True}))
    await session.refresh(row)
    assert utc(row.updated_at) == clock[0]
    assert utc(row.created_at) == OLD


async def test_mapped_core_default_and_explicit_override(session, clock):
    from datetime import timedelta

    from sqlalchemy import update

    row = SystemConfig(name="core-owner", data={}, created_at=OLD, updated_at=OLD)
    session.add(row)
    await session.flush()
    await session.execute(update(SystemConfig).where(SystemConfig.id == row.id).values(data={"core": True}))
    await session.refresh(row)
    assert utc(row.updated_at) == clock[0]
    clock[0] += timedelta(days=1)
    await session.execute(
        update(SystemConfig).where(SystemConfig.id == row.id).values(data={}, updated_at=SystemConfig.updated_at)
    )
    await session.refresh(row)
    assert utc(row.updated_at) == clock[0] - timedelta(days=1)
    await session.execute(
        update(SystemConfig).where(SystemConfig.id == row.id).values(data={"explicit": True}, updated_at=OLD)
    )
    await session.refresh(row)
    assert utc(row.updated_at) == OLD
