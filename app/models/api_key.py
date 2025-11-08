import uuid
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name='{self.name}', active={self.is_active})>"
