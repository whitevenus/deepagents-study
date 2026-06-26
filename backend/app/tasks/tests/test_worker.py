"""tasks 模块 · worker 测试(就近共置,镜像 app/tasks/agent_runtime 的 worker)。
跨模块的 DB 隔离/清表在根 conftest.py;这里只放 worker 专属的 stub 和断言。

为什么 monkeypatch run_task:LLM 输出非确定,不该在单测里断言;这里只测确定性的
调度逻辑。模型那层用 eval(固定数据集 + 通过率)而非单测,留到 Phase 4 / LangSmith。"""

import asyncio
import time

import pytest

from app.agent_runtime import executor, worker
from app.database import SessionLocal
from app.tasks.models import Task


def _stub(title, description, owner_id=None, trace_id=None):
    """模拟 agent:慢任务(测并发),结果带 title(测无串扰),特殊 title 触发异常/卡死。"""
    if title == "BOOM":
        raise RuntimeError("模型炸了")
    if title == "HANG":
        time.sleep(10)  # 超过 TASK_TIMEOUT=1 → wait_for 超时
    time.sleep(0.3)
    return f"result-for-{title}"


executor.run_task = _stub


@pytest.fixture(autouse=True)
def _reset_worker():
    worker._running.clear()
    yield


def _seed(title, description="d", status="pending") -> str:
    db = SessionLocal()
    try:
        t = Task(title=title, description=description, status=status)
        db.add(t)
        db.commit()
        return t.id
    finally:
        db.close()


def _status(task_id) -> str:
    db = SessionLocal()
    try:
        return db.get(Task, task_id).status
    finally:
        db.close()


def _result(task_id) -> str:
    db = SessionLocal()
    try:
        return db.get(Task, task_id).result
    finally:
        db.close()


async def _run_until(ids, timeout=20):
    """启动 worker,等到给定任务全部 settle(done/failed),再停。"""
    stop = asyncio.Event()
    wt = asyncio.create_task(worker.run_worker(stop))
    try:
        for _ in range(int(timeout / 0.1)):
            if all(_status(i) in ("done", "failed") for i in ids):
                return
            await asyncio.sleep(0.1)
        raise AssertionError("超时:任务未全部 settle")
    finally:
        stop.set()
        await wt


def test_concurrency_no_crosstalk():
    """5 个任务并发完成,且每个结果对得上自己的 title(无串扰)= Phase 2 终止条件。"""
    ids = {_seed(f"task-{i}"): f"task-{i}" for i in range(5)}
    asyncio.run(_run_until(list(ids)))
    for tid, title in ids.items():
        assert _status(tid) == "done"
        assert _result(tid) == f"result-for-{title}", f"串扰!{title} 拿到 {_result(tid)}"


def test_retry_then_failed():
    """每次都抛异常的任务,重试到上限后落 failed。"""
    tid = _seed("BOOM")
    asyncio.run(_run_until([tid]))
    assert _status(tid) == "failed"
    assert "重试 2 次" in _result(tid)


def test_timeout_falls_back_to_failed():
    """卡死的任务被 wait_for 超时打断,最终 failed(修 Phase1 永久 in_progress bug)。"""
    tid = _seed("HANG")
    asyncio.run(_run_until([tid]))
    assert _status(tid) == "failed"


def test_recover_stale_resets_in_progress():
    """启动恢复:残留的 in_progress 被重置为 pending(进程重启不丢任务)。"""
    tid = _seed("stuck", status="in_progress")
    n = worker.recover_stale()
    assert _status(tid) == "pending"
    assert n >= 1


def test_cancelled_result_not_overwritten():
    """跑的过程中被取消的任务,worker 完成后不覆盖 cancelled 状态。"""
    tid = _seed("cancel-me", status="cancelled")
    worker._finish(tid, "done", "should-not-write")
    assert _status(tid) == "cancelled"


def test_decompose_creates_children():
    """decomposing 任务被拆成子任务:父落 done,子任务带 parent_id 入库。"""
    executor.decompose = lambda title, desc: [
        {"title": f"sub-{i}", "description": "x"} for i in range(3)
    ]
    tid = _seed("big-task", status="decomposing")
    asyncio.run(_run_until([tid]))
    assert _status(tid) == "done"
    db = SessionLocal()
    try:
        children = db.query(Task).filter(Task.parent_id == tid).all()
    finally:
        db.close()
    assert len(children) == 3
    assert {c.parent_id for c in children} == {tid}
