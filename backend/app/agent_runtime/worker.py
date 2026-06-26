"""Phase 2 后台 worker:轮询 pending 队列 → 并发执行 → 超时/重试/卡死恢复。

解耦发布与执行:POST 只入库(pending),不再直接跑 agent;执行交给这个独立循环。
ponytail: 进程内 asyncio 轮询 + 空闲槽位限流,不上 Celery/Redis——单机并发够用;
真要跨机分布式或持久队列再换。
"""

import asyncio
import os

from app.agent_runtime import executor  # 通过模块引用,便于测试 monkeypatch run_task
from app.audit.log import record
from app.database import SessionLocal
from app.observability import new_trace_id
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


def _claim(limit: int) -> list[tuple[str, str, str, str, str | None]]:
    """取至多 limit 个待办,返回 (id, title, description, kind, owner_id)。kind=pending|decomposing。
    pending 标记为 in_progress;decomposing 不改状态(靠 _running 防重复派发,崩溃后能自愈不丢拆解意图)。"""
    db = SessionLocal()
    try:
        rows = (
            db.query(Task)
            .filter(Task.status.in_(("pending", "decomposing")))
            .order_by(Task.created_at)
            .all()
        )
        claimed = []
        for t in rows:
            if t.id in _running:  # decomposing 状态不变,需显式跳过正在跑的
                continue
            kind = t.status
            if kind == "pending":
                t.status = "in_progress"
            claimed.append((t.id, t.title, t.description, kind, t.owner_id))
            if len(claimed) >= limit:
                break
        db.commit()
        # 审计:worker 把 pending 接单 → in_progress(谁=worker,做了什么=认领开跑)
        for tid, _, _, kind, _ in claimed:
            if kind == "pending":
                record(actor="worker", action="in_progress", object_id=tid)
        return claimed
    finally:
        db.close()


def _decompose_blocking(task_id: str, title: str, description: str) -> int:
    """调 LLM 拆任务 → 把子任务作为 pending 子记录入库,返回子任务数。"""
    subs = executor.decompose(title, description)
    db = SessionLocal()
    try:
        parent = db.get(Task, task_id)
        owner_id = parent.owner_id if parent else None  # 子任务继承父任务归属人
        db.add_all(
            [
                Task(title=s["title"], description=s["description"], parent_id=task_id, owner_id=owner_id)
                for s in subs
            ]
        )
        db.commit()
        return len(subs)
    finally:
        db.close()


def _remember(
    task_id: str, title: str, description: str, result: str, owner_id: str | None, status: str
) -> None:
    """复盘 + 沉淀(Phase 6):让 reflect 把结果提炼成可复用「教训」再存(替代原文整段,库更精)。
    best-effort + is_pg 守卫(SQLite 测试自动 no-op,且不会触达 LLM);任何失败都不影响任务完成。"""
    try:
        from app.knowledge.store import add_knowledge, is_pg

        if not (is_pg() and result):
            return
        refl = executor.reflect(title, description, result, status)
        # 存储闸:只存「值得复用」的教训(失败/不显然洞见),挡掉常规成功的废话教训污染知识库
        if refl["reusable"] and refl["lesson"].strip():
            add_knowledge(
                f"任务:{title}\n教训:{refl['lesson']}", source_task_id=task_id, owner_id=owner_id
            )
    except Exception:  # noqa: BLE001  沉淀失败不能拖垮任务
        pass


def _finish(task_id: str, status: str, result: str, trace_id: str | None = None) -> None:
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
    # 审计:谁=agent,做了什么=最终落 done/failed,trace_id 串到 Langfuse 看 agent 怎么干的。
    # 放在 commit 之后、仅成功路径执行(cancelled/不存在已 return),保证审计反映真实落库结果。
    record(actor="agent", action=status, object_id=task_id, detail=result, trace_id=trace_id)


async def _run(task_id: str, title: str, description: str, kind: str, owner_id: str | None) -> None:
    last_err = None
    trace_id = new_trace_id()  # None when Langfuse 未配;非 None 时 agent 轨迹进 Langfuse + 写审计
    try:
        for _ in range(MAX_ATTEMPTS):
            try:
                # to_thread:阻塞的 LLM 调用;wait_for:超时兜底,避免永久卡死
                if kind == "decomposing":
                    n = await asyncio.wait_for(
                        asyncio.to_thread(_decompose_blocking, task_id, title, description),
                        TASK_TIMEOUT,
                    )
                    _finish(task_id, "done", f"已拆解为 {n} 个子任务")
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(
                            executor.run_task, title, description, owner_id, trace_id
                        ),
                        TASK_TIMEOUT,
                    )
                    _finish(task_id, "done", result, trace_id)
                    # 复盘提炼教训入库
                    await asyncio.to_thread(
                        _remember, task_id, title, description, result, owner_id, "done"
                    )
                return
            except Exception as e:  # noqa: BLE001  含 TimeoutError;重试到上限再判失败
                last_err = e
        # str(TimeoutError()) 是空串 → 兜底用异常类名,避免显示「执行失败:」后空白
        fail_msg = f"执行失败(重试 {MAX_ATTEMPTS} 次):{str(last_err) or type(last_err).__name__}"
        _finish(task_id, "failed", fail_msg, trace_id)
        # 失败也复盘:提炼「这类任务为何失败、下次怎么避免」,供相似任务参考
        await asyncio.to_thread(_remember, task_id, title, description, fail_msg, owner_id, "failed")
    finally:
        _running.discard(task_id)


async def run_worker(stop_event: asyncio.Event | None = None) -> None:
    recover_stale()
    while stop_event is None or not stop_event.is_set():
        free = MAX_CONCURRENCY - len(_running)
        if free > 0:
            for task_id, title, desc, kind, owner_id in _claim(free):
                _running.add(task_id)
                asyncio.create_task(_run(task_id, title, desc, kind, owner_id))
        await asyncio.sleep(POLL_INTERVAL)
