"""知识库:沉淀历史经验 + 向量相似度检索(pgvector)。

PG/pgvector 专属。SQLite(测试)下 is_pg()=False,init/add/search 全部安全跳过——
所以走 SQLite 的单测不会碰到这里,真实检索能力用 demo/eval 验(同 worker:LLM/外部那层不进单测)。
"""

from sqlalchemy import text

from app.config import EMBED_DIM
from app.database import engine
from app.knowledge.embed import embed


def is_pg() -> bool:
    return engine.dialect.name == "postgresql"


def vec_literal(v: list[float]) -> str:
    """向量 → pgvector 字面量 '[0.1,0.2,...]',避免注册 psycopg 适配器,直接 CAST 即可。"""
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


def init_knowledge() -> None:
    if not is_pg():
        return
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id BIGSERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({EMBED_DIM}) NOT NULL,
                    source_task_id VARCHAR,
                    owner_id VARCHAR,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
                """
            )
        )
        # 给已存在的旧表补 owner_id(同 tasks 的 ensure_columns 思路;上 Alembic 前的过渡)
        conn.execute(text("ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS owner_id VARCHAR"))


def add_knowledge(content: str, source_task_id: str | None = None, owner_id: str | None = None) -> None:
    if not is_pg():
        return
    vec = vec_literal(embed(content))
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO knowledge (content, embedding, source_task_id, owner_id) "
                "VALUES (:c, CAST(:e AS vector), :s, :o)"
            ),
            {"c": content, "e": vec, "s": source_task_id, "o": owner_id},
        )


def search_knowledge(query: str, k: int = 3, owner_id: str | None = None) -> list[dict]:
    """返回最相关的 k 条:[{content, score}],score=余弦相似度(1 - 余弦距离),越大越像。

    数据权限:按 owner_id 隔离(对齐 Phase 3 的 ABAC「own」)——只检索 owner 一致的知识,
    避免跨用户泄漏。`IS NOT DISTINCT FROM` 是 NULL 安全等值:owner_id=None 只匹配无主(seed)知识,
    传具体用户只匹配该用户的知识。"""
    if not is_pg():
        return []
    vec = vec_literal(embed(query))
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT content, 1 - (embedding <=> CAST(:q AS vector)) AS score "
                "FROM knowledge WHERE owner_id IS NOT DISTINCT FROM :o "
                "ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"
            ),
            {"q": vec, "k": k, "o": owner_id},
        ).all()
    return [{"content": c, "score": float(s)} for c, s in rows]
