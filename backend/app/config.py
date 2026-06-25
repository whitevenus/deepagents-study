import os

from dotenv import load_dotenv

load_dotenv()  # 读项目根的 .env(模型 key 等)

# 开发/生产用 Postgres+pgvector(.env 里的 DATABASE_URL);默认值留 SQLite 兜底,
# 测试由 conftest 覆盖成临时 SQLite(快、无外部依赖)。
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./autoboard.db")

# ---- 知识库 embedding(Phase 4)----
# 维度必须与模型一致(Qwen3-Embedding-4B = 2560),pgvector 建表要用它。
EMBED_MODEL = os.getenv("EMBED_MODEL", "Qwen/Qwen3-Embedding-4B")
EMBED_DIM = int(os.getenv("EMBED_DIM", "2560"))

# JWT 签名密钥。ponytail: 开发给个默认值;生产必须用 env 注入强随机密钥。
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-in-prod-please-32b+")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "12"))
