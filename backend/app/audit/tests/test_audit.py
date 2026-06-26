"""Phase 5 终止条件:任一任务可完整追溯 谁/哪个 agent/做了什么/何时。

两层:
1) 接缝直写(确定性):worker 接单→done 写出有序审计轨迹;_finish 对 cancelled 不补写。
2) 端到端(裸 app + TestClient):create/cancel 落审计;GET /audit 返回有序轨迹;越权读被拒。

Langfuse 可观测层(trace_id 串联)是 env-gated 外部依赖,同本项目惯例用真实 e2e/demo 验,不进单测。
"""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent_runtime import executor, worker
from app.audit.log import trail
from app.auth.security import make_token
from app.database import SessionLocal, get_db
from app.tasks.models import Task
from app.tasks.router import router


def _auth(username):
    return {"Authorization": f"Bearer {make_token(username)}"}


@pytest.fixture(autouse=True)
def _reset_worker():
    worker._running.clear()
    yield


# ---- 接缝直写:worker 跑完留下有序审计 ----

def test_worker_writes_ordered_trail(monkeypatch):
    """pending → worker 接单(in_progress)→ agent 完成(done),审计是一条有序时间线。"""
    monkeypatch.setattr(
        executor, "run_task", lambda title, description, owner_id=None, trace_id=None: f"r-{title}"
    )
    db = SessionLocal()
    t = Task(title="audit-me", status="pending", owner_id="alice")
    db.add(t)
    db.commit()
    tid = t.id
    db.close()

    async def go():
        stop = asyncio.Event()
        wt = asyncio.create_task(worker.run_worker(stop))
        for _ in range(200):
            if SessionLocal().get(Task, tid).status == "done":
                break
            await asyncio.sleep(0.05)
        stop.set()
        await wt

    asyncio.run(go())

    events = trail(tid)
    assert [(e.actor, e.action) for e in events] == [
        ("worker", "in_progress"),
        ("agent", "done"),
    ]


def test_finish_skips_audit_for_cancelled():
    """跑的过程中被取消的任务,_finish 不覆盖状态,也不补写一条假的 done 审计。"""
    db = SessionLocal()
    t = Task(title="x", status="cancelled", owner_id="alice")
    db.add(t)
    db.commit()
    tid = t.id
    db.close()

    worker._finish(tid, "done", "should-not-write")
    assert trail(tid) == []


# ---- 端到端:API 落审计 + 可追溯 + 越权读被拒 ----

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = _override_db
    return TestClient(app, raise_server_exceptions=True)


def _override_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_then_cancel_traceable(client):
    """建任务→取消,审计完整记下 谁/做了什么/何时,且 GET /audit 按时间正序返回。"""
    r = client.post("/tasks", json={"title": "trace-job"}, headers=_auth("alice"))
    tid = r.json()["id"]
    client.post(f"/tasks/{tid}/cancel", headers=_auth("alice"))

    r = client.get(f"/tasks/{tid}/audit", headers=_auth("alice"))
    assert r.status_code == 200
    trail_ = r.json()
    assert [(e["actor"], e["action"]) for e in trail_] == [
        ("alice", "created"),
        ("alice", "cancelled"),
    ]
    assert all(e["created_at"] for e in trail_)  # 何时


def test_audit_read_denied_for_unauthorized(client):
    """member 看不到别人任务的审计(复用任务读权限,403)。"""
    r = client.post("/tasks", json={"title": "alice-job"}, headers=_auth("alice"))
    tid = r.json()["id"]
    assert client.get(f"/tasks/{tid}/audit", headers=_auth("bob")).status_code == 403
