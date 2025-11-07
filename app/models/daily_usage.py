from datetime import date
import uuid

from sqlalchemy import Column, Date, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class DailyUsage(Base):
    __tablename__ = "daily_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)  # Use Integer for SQLite compatibility
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False, index=True)
    day = Column(Date, nullable=False)
    count = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint('api_key_id', 'day', name='uq_daily_usage_api_key_day'),
    )

    def __repr__(self) -> str:
        return f"<DailyUsage(id={self.id}, api_key_id={self.api_key_id}, day={self.day}, count={self.count})>"