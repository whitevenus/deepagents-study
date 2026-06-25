"""Phase 3.5 认证(authn):密码哈希 / JWT / 登录端点。
authz(Casbin 权限)在 test_permissions.py;这里只测「你是谁」。"""

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.models import User
from app.auth.router import router
from app.auth.security import hash_password, make_token, read_token, verify_password
from app.database import SessionLocal, get_db


def test_password_hash_roundtrip():
    h = hash_password("hunter2")
    assert h != "hunter2"  # 不是明文
    assert verify_password("hunter2", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    assert read_token(make_token("alice")) == "alice"


def test_jwt_tampered_rejected():
    with pytest.raises(jwt.PyJWTError):
        read_token(make_token("alice") + "x")


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = _override_db
    return TestClient(app)


def _override_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_user(username="alice", password="alice"):
    db = SessionLocal()
    try:
        db.add(User(username=username, password_hash=hash_password(password)))
        db.commit()
    finally:
        db.close()


def test_login_success_returns_token(client):
    _seed_user("alice", "alice")
    r = client.post("/auth/login", data={"username": "alice", "password": "alice"})
    assert r.status_code == 200
    assert read_token(r.json()["access_token"]) == "alice"


def test_login_wrong_password_401(client):
    _seed_user("alice", "alice")
    r = client.post("/auth/login", data={"username": "alice", "password": "nope"})
    assert r.status_code == 401


def test_login_unknown_user_401(client):
    r = client.post("/auth/login", data={"username": "ghost", "password": "x"})
    assert r.status_code == 401


def test_me_returns_username_and_roles(client):
    # alice 在 policy.csv 里是 admin(g, alice, admin)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {make_token('alice')}"})
    assert r.status_code == 200
    assert r.json()["username"] == "alice"
    assert "admin" in r.json()["roles"]
