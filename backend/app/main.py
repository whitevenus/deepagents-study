import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent_runtime.worker import run_worker
from app.auth import models as auth_models  # noqa: F401  注册 User 到 Base.metadata
from app.auth.router import router as auth_router
from app.auth.security import hash_password
from app.database import Base, SessionLocal, engine, ensure_columns
from app.knowledge.store import init_knowledge
from app.tasks import models  # noqa: F401  注册模型到 Base.metadata
from app.tasks.router import router as tasks_router

# Phase 3.5 demo:种子用户(角色由 policy.csv 的 g 策略管)。密码=用户名,生产删掉这套。
_DEMO_USERS = ["alice", "bob", "carol"]


def seed_demo_users() -> None:
    db = SessionLocal()
    try:
        for name in _DEMO_USERS:
            if not db.query(auth_models.User).filter_by(username=name).first():
                db.add(auth_models.User(username=name, password_hash=hash_password(name)))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ponytail: MVP 直接建表;有 schema 变更需求时再上 Alembic(参考 references/.../backend/alembic)。
    Base.metadata.create_all(bind=engine)
    ensure_columns()  # 给旧库补新列(parent_id 等)
    init_knowledge()  # Phase 4:建 pgvector 扩展 + knowledge 表(SQLite 自动跳过)
    seed_demo_users()
    worker = asyncio.create_task(run_worker())  # Phase 2:进程内后台 worker 接单
    yield
    worker.cancel()


app = FastAPI(title="AutoBoard", lifespan=lifespan)

# MVP 本地开发放开 CORS;生产收紧到具体前端域名。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tasks_router)


@app.get("/health")
def health():
    return {"status": "ok"}
