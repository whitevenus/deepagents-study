import os

from dotenv import load_dotenv

load_dotenv()  # 读项目根的 .env(模型 key 等)

# MVP 用 SQLite,零配置;换 Postgres 只改这一个连接串(以后接 pgvector 也从这里)。
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./autoboard.db")
