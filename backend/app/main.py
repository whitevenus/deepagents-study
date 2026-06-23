from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.tasks import models  # noqa: F401  注册模型到 Base.metadata
from app.tasks.router import router as tasks_router

# ponytail: MVP 直接建表;有 schema 变更需求时再上 Alembic(参考 references/.../backend/alembic)。
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AutoBoard")

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
