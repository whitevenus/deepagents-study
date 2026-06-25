import os

from dotenv import load_dotenv

load_dotenv()  # 读项目根的 .env(模型 key 等)

# MVP 用 SQLite,零配置;换 Postgres 只改这一个连接串(以后接 pgvector 也从这里)。
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./autoboard.db")

# JWT 签名密钥。ponytail: 开发给个默认值;生产必须用 env 注入强随机密钥。
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-in-prod-please-32b+")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "12"))
