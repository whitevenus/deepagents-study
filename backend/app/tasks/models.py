import uuid

from sqlalchemy import Column, DateTime, String, Text

from app.clock import now
from app.database import Base


def _uuid() -> str:
    # ponytail: MVP 用 stdlib uuid4;若以后要时间有序主键再换 uuid7/雪花。
    return str(uuid.uuid4())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    # pending | decomposing | in_progress | done | failed | cancelled
    status = Column(String, default="pending")
    result = Column(Text, default="")
    parent_id = Column(String, index=True, nullable=True)  # 子任务指向父任务;顶层任务为 None
    owner_id = Column(String, index=True, nullable=True)   # 任务拥有者(创建人);行级数据权限按此判定

    created_at = Column(DateTime(timezone=True), default=now)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)
