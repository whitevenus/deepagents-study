import uuid

from sqlalchemy import Column, DateTime, String, Text

from app.clock import now
from app.database import Base


class AuditLog(Base):
    """业务审计日志(append-only,只写不改不删)。

    回答终止条件「谁/哪个 agent/做了什么/何时」:actor(谁)+ action(做了什么)+
    object(对哪条数据)+ created_at(何时)。trace_id 串到 Langfuse 看 agent「为什么这么做」。
    ponytail: 纯列(非 pgvector),走 ORM 即可,SQLite/PG 通用,单测能覆盖。
    """

    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor = Column(String, nullable=False)         # 谁:用户名 / "worker" / "agent"
    action = Column(String, nullable=False)        # 做了什么:created/in_progress/done/failed/cancelled/decomposed
    object_type = Column(String, nullable=False)   # 对什么:目前只有 "task"
    object_id = Column(String, index=True, nullable=False)
    detail = Column(Text, default="")              # 结果预览 / 失败原因 / 前后值摘要
    trace_id = Column(String, nullable=True)       # 串到 Langfuse 的 trace(可观测层,看「为什么」)
    created_at = Column(DateTime(timezone=True), default=now)
