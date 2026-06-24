"""Phase 2 后台 worker:轮询 pending 队列 → 并发执行 → 超时/重试/卡死恢复。

解耦发布与执行:POST 只入库(pending),不再直接跑 agent;执行交给这个独立循环。
ponytail: 进程内 asyncio 轮询 + 空闲槽位限流,不上 Celery/Redis——单机并发够用;
真要跨机分布式或持久队列再换。
"""

import asyncio
import os

from app.agent_runtime import executor  # 通过模块引用,便于测试 monkeypatch run_task
from app.database import SessionLocal
from app.tasks.models import Task

POLL_INTERVAL = float(os.getenv("WORKER_POLL_INTERVAL", "1.0"))  # 秒,扫一次 pending
MAX_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "5"))      # 同时跑几个(= Phase2 终止条件:5 并发)
TASK_TIMEOUT = float(os.getenv("TASK_TIMEOUT", "180"))           # 秒,单任务硬超时(修 ChatOpenAI 无 timeout 卡死)
MAX_ATTEMPTS = int(os.getenv("TASK_MAX_ATTEMPTS", "3"))          # 失败重试次数

_running: set[str] = set()  # 正在跑的 task_id;空闲槽位 = MAX_CONCURRENCY - len(_running)


def recover_stale() -> int:
    """启动时把上次进程残留的 in_progress 重置为 pending(进程重启/崩溃不丢任务)。"""
    db = SessionLocal()
    try:
        n = db.query(Task).filter(Task.status == "in_progress").update({"status": "pending"})
        db.commit()
        return n
    finally:
        db.close()


def _claim_pending(limit: int) -> list[tuple[str, str, str]]:
    """取至多 limit 个 pending,标记 in_progress,返回 (id, title, description)。
    单循环串行 claim,不会重复派发同一任务。"""
    db = SessionLocal()
    try:
        rows = (
            db.query(Task)
            .filter(Task.status == "pending")
            .order_by(Task.created_at)
            .limit(limit)
            .all()
        )
        claimed = [(t.id, t.title, t.description) for t in rows]
        for t in rows:
            t.status = "in_progress"
        db.commit()
        return claimed
    finally:
        db.close()


def _finish(task_id: str, status: str, result: str) -> None:
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if not task or task.status == "cancelled":  # 跑的过程中被取消 → 不覆盖
            return
        task.status = status
        task.result = result
        db.commit()
    finally:
        db.close()


async def _run(task_id: str, title: str, description: str) -> None:
    last_err = None
    try:
        for _ in range(MAX_ATTEMPTS):
            try:
                # to_thread:run_task 是阻塞的 deepagents 调用;wait_for:超时兜底,避免永久卡死
                result = await asyncio.wait_for(
                    asyncio.to_thread(executor.run_task, title, description), TASK_TIMEOUT
                )
                _finish(task_id, "done", result)
                return
            except Exception as e:  # noqa: BLE001  含 TimeoutError;重试到上限再判失败
                last_err = e
        _finish(task_id, "failed", f"执行失败(重试 {MAX_ATTEMPTS} 次):{last_err}")
    finally:
        _running.discard(task_id)


async def run_worker(stop_event: asyncio.Event | None = None) -> None:
    recover_stale()
    while stop_event is None or not stop_event.is_set():
        free = MAX_CONCURRENCY - len(_running)
        if free > 0:
            for task_id, title, desc in _claim_pending(free):
                _running.add(task_id)
                asyncio.create_task(_run(task_id, title, desc))
        await asyncio.sleep(POLL_INTERVAL)
