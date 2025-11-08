import uuid
from typing import Optional

from sqlalchemy import Date, Integer, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyUsage(Base):
    __tablename__ = "daily_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False, index=True)
    day: Mapped[Date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint("api_key_id", "day", name="uq_daily_usage_api_key_day"),)

    def __repr__(self) -> str:
        return f"<DailyUsage(id={self.id}, api_key_id={self.api_key_id}, day={self.day}, count={self.count})>"
