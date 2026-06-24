from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

# check_same_thread=False:SQLite 在 FastAPI 多线程下需要。换 Postgres 时去掉 connect_args。
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_columns():
    """ponytail: 上 Alembic 前的极简补列——给已存在的旧库补上新加的列(新建库由 create_all 直接带上)。
    加新列就在这加一行;真要正经迁移历史再换 Alembic。"""
    from sqlalchemy import inspect, text

    existing = {c["name"] for c in inspect(engine).get_columns("tasks")}
    with engine.begin() as conn:
        if "parent_id" not in existing:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN parent_id VARCHAR"))
