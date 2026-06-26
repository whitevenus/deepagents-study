"""审计写入/读取(接缝直写:在真正改 DB 的地方记一笔)。

ponytail: 不用 deepagents middleware 拦工具调用——那些是 agent 内部步骤,归 Langfuse 可观测层;
业务数据变更全发生在 router/worker 的 DB 写入处,直接在接缝记一笔更简单、不耦合框架内部。
"""

from app.audit.models import AuditLog
from app.database import SessionLocal


def record(
    actor: str,
    action: str,
    object_id: str,
    object_type: str = "task",
    detail: str = "",
    trace_id: str | None = None,
) -> None:
    """记一条审计(append-only)。自开独立 session,不耦合调用方的请求事务,worker 里也能直接用。
    best-effort:审计失败绝不拖垮主流程。"""
    db = SessionLocal()
    try:
        db.add(
            AuditLog(
                actor=actor,
                action=action,
                object_type=object_type,
                object_id=object_id,
                detail=(detail or "")[:2000],  # 别把超长结果整段灌进审计,留预览
                trace_id=trace_id,
            )
        )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    finally:
        db.close()


def trail(object_id: str) -> list[AuditLog]:
    """取某条数据的完整审计轨迹,按时间正序(最早在前 = 一条时间线)。"""
    db = SessionLocal()
    try:
        return (
            db.query(AuditLog)
            .filter(AuditLog.object_id == object_id)
            .order_by(AuditLog.created_at)
            .all()
        )
    finally:
        db.close()
