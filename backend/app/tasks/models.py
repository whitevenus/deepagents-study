import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text

from app.database import Base


def _uuid() -> str:
    # ponytail: MVP 用 stdlib uuid4;若以后要时间有序主键再换 uuid7/雪花。
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="pending")  # pending | in_progress | done | failed
    result = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
