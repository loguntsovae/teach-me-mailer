from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class SendLog(Base):
    __tablename__ = "send_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    recipient = Column(String(255), nullable=False)
    message_id = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SendLog(id={self.id}, recipient='{self.recipient}', sent_at='{self.sent_at}')>"