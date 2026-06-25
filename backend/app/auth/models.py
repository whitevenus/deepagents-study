import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from app.database import Base


class User(Base):
    """认证用的用户表:只存「你是谁」(用户名+密码哈希)。
    「你是什么角色」由 Casbin 的 g 策略管(policy.csv),不在这重复存,避免两处真相打架。"""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
