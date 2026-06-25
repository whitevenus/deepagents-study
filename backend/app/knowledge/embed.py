"""文本 → 向量。复用 SiliconFlow(OpenAI 兼容)的 embedding 接口。
deepagents 自身无向量检索,这是我们自接 pgvector 的第一环(Ch8 早就埋的坑)。"""

import os

import httpx

from app.config import EMBED_MODEL

_URL = "https://api.siliconflow.cn/v1/embeddings"


def embed(text: str) -> list[float]:
    r = httpx.post(
        _URL,
        headers={"Authorization": f"Bearer {os.environ['SILICONFLOW_API_KEY']}"},
        json={"model": EMBED_MODEL, "input": text},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]
