"""共享测试基建(FBA 风格:跨模块复用的 fixture 集中放根 conftest)。
具体用例就近放在各模块的 tests/ 子包里(如 app/tasks/tests/)。

为什么在这里设环境:app.* 在 import 时就读 DATABASE_URL 建 engine,
必须在任何 app 导入之前把数据库指到临时库,绝不碰开发库 autoboard.db。"""

import os
import tempfile

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_db.name}"
os.environ["WORKER_POLL_INTERVAL"] = "0.05"
os.environ["TASK_MAX_ATTEMPTS"] = "2"
os.environ["TASK_TIMEOUT"] = "1"

import pytest  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.tasks import models  # noqa: E402,F401  注册模型到 Base.metadata

Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_db():
    """每个测试前清空所有表,保证用例隔离。新增模型后自动覆盖,无需改这里。"""
    db = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()
    yield


def pytest_unconfigure(config):
    try:
        os.unlink(_db.name)
    except OSError:
        pass
