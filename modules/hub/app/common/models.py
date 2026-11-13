"""Hub-owned timestamp policy for mapped ORM and Core writes."""

from datetime import datetime

from app_layer_base.base.models.mixin import TimestampMixin as FrameworkTimestampMixin
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin(FrameworkTimestampMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=get_current_utc_time,
        nullable=False,
    )
