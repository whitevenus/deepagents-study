import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent_runtime.worker import run_worker
from app.database import Base, engine, ensure_columns
from app.tasks import models  # noqa: F401  注册模型到 Base.metadata
from app.tasks.router import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ponytail: MVP 直接建表;有 schema 变更需求时再上 Alembic(参考 references/.../backend/alembic)。
    Base.metadata.create_all(bind=engine)
    ensure_columns()  # 给旧库补新列(parent_id 等)
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

app.include_router(tasks_router)


@app.get("/health")
def health():
    return {"status": "ok"}
