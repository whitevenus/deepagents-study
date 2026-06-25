"""Phase 3 终止条件:权限矩阵单测通过 + 越权被拒。

两层:
1) 权限矩阵(纯 Casbin,确定性):角色 × 动作 × 拥有者 → 准/拒。
2) 端到端越权拦截(裸 FastAPI app + TestClient):缺身份 401、越权 403。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.permissions import can, data_scope
from app.auth.security import make_token
from app.database import SessionLocal, get_db
from app.tasks.models import Task
from app.tasks.router import router


def _auth(username):
    """带真实 JWT 的请求头(替代旧的 X-User-Id stub)。"""
    return {"Authorization": f"Bearer {make_token(username)}"}

# 用户:alice=admin, bob=member, carol=viewer(见 policy.csv)
OTHER = "someone-else"

# (user, obj, act, owner, 期望)。owner=user 表示操作自己的对象。
MATRIX = [
    # admin 全通
    ("alice", "task", "create", "alice", True),
    ("alice", "task", "read", OTHER, True),
    ("alice", "task", "cancel", OTHER, True),
    ("alice", "user", "manage", "alice", True),
    # member:能建;只能读/取消自己的
    ("bob", "task", "create", "bob", True),
    ("bob", "task", "read", "bob", True),
    ("bob", "task", "read", OTHER, False),     # 越权:读别人的
    ("bob", "task", "cancel", "bob", True),
    ("bob", "task", "cancel", OTHER, False),   # 越权:取消别人的
    ("bob", "user", "manage", "bob", False),   # 越权:无用户管理权
    # viewer:只能读(全部),不能建/取消
    ("carol", "task", "read", OTHER, True),
    ("carol", "task", "create", "carol", False),
    ("carol", "task", "cancel", "carol", False),
    # 未知用户(无角色):一律拒
    ("ghost", "task", "read", "ghost", False),
    ("ghost", "task", "create", "ghost", False),
]


@pytest.mark.parametrize("user,obj,act,owner,expected", MATRIX)
def test_permission_matrix(user, obj, act, owner, expected):
    assert can(user, obj, act, owner=owner) is expected


def test_data_scope():
    assert data_scope("alice", "task", "read") == "all"   # admin 看全部
    assert data_scope("carol", "task", "read") == "all"   # viewer 看全部
    assert data_scope("bob", "task", "read") == "own"     # member 只看自己的
    assert data_scope("bob", "user", "manage") is None    # 无权
    assert data_scope("ghost", "task", "read") is None


# ---- 端到端越权拦截 ----

@pytest.fixture
def client():
    """裸 app:只挂 tasks 路由,不起 lifespan/worker(避免后台轮询跑真 LLM)。"""
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


def _seed(owner_id, status="pending") -> str:
    db = SessionLocal()
    try:
        t = Task(title="t", owner_id=owner_id, status=status)
        db.add(t)
        db.commit()
        return t.id
    finally:
        db.close()


def test_missing_token_401(client):
    assert client.get("/tasks").status_code == 401


def test_bad_token_401(client):
    r = client.get("/tasks", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401


def test_viewer_cannot_create_403(client):
    r = client.post("/tasks", json={"title": "x"}, headers=_auth("carol"))
    assert r.status_code == 403


def test_member_cannot_cancel_others_task_403(client):
    tid = _seed(owner_id="alice")
    r = client.post(f"/tasks/{tid}/cancel", headers=_auth("bob"))
    assert r.status_code == 403


def test_member_can_cancel_own_task(client):
    tid = _seed(owner_id="bob")
    r = client.post(f"/tasks/{tid}/cancel", headers=_auth("bob"))
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_member_list_only_sees_own(client):
    _seed(owner_id="alice")
    _seed(owner_id="bob")
    r = client.get("/tasks", headers=_auth("bob"))
    assert r.status_code == 200
    assert {t["owner_id"] for t in r.json()} == {"bob"}
