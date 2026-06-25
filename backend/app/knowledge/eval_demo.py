"""Phase 4 终止条件的可运行检查:固定基准下,相似查询能检索到对的历史知识(更准的地基)。

需要真 PG + embedding API(读 .env)。手动跑,不进 CI(同 worker:外部那层用 eval 不用单测):
    uv run python -m app.knowledge.eval_demo   # 在项目根,带 .env

断言:语义相似的查询,Top1 命中预期那条,且分数明显高于不相关那条。
"""

from sqlalchemy import text

from app.database import engine
from app.knowledge.store import add_knowledge, init_knowledge, is_pg, search_knowledge

# 固定基准:3 条不同主题的历史知识
SEED = [
    "任务:实现斐波那契数列。结果:用动态规划自底向上迭代,避免递归重复计算,时间 O(n) 空间 O(1)。",
    "任务:配置 Nginx 反向代理。结果:在 server 块用 location 配 proxy_pass,记得设 proxy_set_header Host。",
    "任务:做一份水果沙拉。结果:苹果香蕉切丁,加酸奶和蜂蜜拌匀,冷藏后更好吃。",
]
# 与第 0 条语义相似、但用词不同的查询
QUERY = "怎么高效计算 fibonacci,别用慢的递归"


def main() -> None:
    assert is_pg(), "需要连到 Postgres(检查 .env 的 DATABASE_URL),当前不是 PG"
    init_knowledge()
    with engine.begin() as conn:  # 清表,保证固定基准可重复
        conn.execute(text("TRUNCATE knowledge"))
    for s in SEED:
        add_knowledge(s, owner_id="alice")

    # ① 检索更准:alice 查自己的知识,语义相似 Top1 命中斐波那契
    hits = search_knowledge(QUERY, k=3, owner_id="alice")
    print(f"查询(alice):{QUERY}\n")
    for i, h in enumerate(hits):
        print(f"#{i + 1}  相似度 {h['score']:.3f}  {h['content'][:40]}…")
    top = hits[0]
    assert "斐波那契" in top["content"], f"Top1 不是斐波那契那条,而是:{top['content'][:40]}"
    assert top["score"] - hits[-1]["score"] > 0.05, "相关 vs 不相关 区分度不够"
    print("✅ 检索更准:语义相似查询 Top1 命中斐波那契,且明显高于不相关条目。\n")

    # ② 数据权限:bob 存一条同主题知识,alice 检索时绝不能看到(对齐 Phase 3 ABAC)
    add_knowledge("任务:斐波那契。结果:这是 BOB 的私有结论,不该被别人检索到。", owner_id="bob")
    alice_hits = search_knowledge(QUERY, k=5, owner_id="alice")
    assert all("BOB" not in h["content"] for h in alice_hits), "越权!alice 检索到了 bob 的知识"
    bob_hits = search_knowledge(QUERY, k=5, owner_id="bob")
    assert bob_hits and "BOB" in bob_hits[0]["content"], "bob 应能检索到自己的知识"
    assert all("斐波那契" not in h["content"] or "BOB" in h["content"] for h in bob_hits), (
        "bob 不该看到 alice 的知识"
    )
    print("✅ 数据权限隔离:alice 检索不到 bob 的私有知识,bob 只看到自己的——越权已堵。")


if __name__ == "__main__":
    main()
