"""知识库纯逻辑单测(不碰 PG/API,跟着 SQLite 测试跑)。
真实 embedding + pgvector 检索能力用 eval_demo.py 验(外部那层不进单测,同 worker 的 LLM)。"""

from app.knowledge.store import is_pg, vec_literal


def test_vec_literal():
    assert vec_literal([0.1, 0.2, -3.0]) == "[0.1,0.2,-3.0]"
    assert vec_literal([1, 2]) == "[1.0,2.0]"  # int 也归一成 float


def test_knowledge_noop_on_sqlite():
    # 测试库是 SQLite → 知识库整体安全跳过,search 返回空而不是报错
    from app.knowledge.store import search_knowledge

    assert not is_pg()
    assert search_knowledge("anything") == []
