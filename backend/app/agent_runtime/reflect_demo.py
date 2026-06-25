"""Phase 6 自我进化 demo:复盘裁判 + 提炼教训,且教训能被相似任务检索复用。

需真 PG + LLM API(读 .env)。手动跑(项目根):
    PYTHONPATH=backend uv run python -m app.agent_runtime.reflect_demo

证明:① reflect 把达标/不达标判对,并对不达标结果给出纠正教训;
     ② 提炼的教训入库后,相似任务能检索到(对接预检索注入 → 第二轮更好)。
"""

from sqlalchemy import text

from app.agent_runtime.executor import reflect
from app.database import engine
from app.knowledge.store import add_knowledge, init_knowledge, is_pg, search_knowledge

LEAP_TASK = "用 Python 写函数判断闰年。要求正确处理世纪年:能被 100 整除但不能被 400 整除的年份不是闰年。"


def main() -> None:
    # ① 裁判 + 提炼
    good = reflect("计算 1+1 等于几", "", "1 + 1 = 2。")
    bad = reflect(LEAP_TASK, "", "def is_leap(y):\n    return y % 4 == 0")  # 漏了世纪年规则
    print("好结果裁判:", good)
    print("坏结果裁判:", bad)
    assert good["adequate"] is True, "正确结果应判达标"
    assert good["reusable"] is False, "常规简单成功不该值得存(存储闸应挡掉)"
    assert bad["adequate"] is False, "漏世纪年规则的代码应判不达标"
    assert bad["reusable"] is True and bad["lesson"], "不达标应判值得存并给出纠正教训"
    print("✅ 裁判+存储闸:常规成功不入库,有 bug 的不达标→值得存→给纠正教训\n")

    # ② 教训入库 → 相似任务可检索复用
    assert is_pg(), "需连 Postgres(检查 .env DATABASE_URL)"
    init_knowledge()
    with engine.begin() as c:
        c.execute(text("TRUNCATE knowledge"))
    add_knowledge(f"任务:{LEAP_TASK}\n教训:{bad['lesson']}", owner_id="alice")

    hits = search_knowledge("怎么正确判断闰年,别漏了世纪年", k=3, owner_id="alice")
    print(f"检索:{hits[0]['content'][:60]}…(相似度 {hits[0]['score']:.2f})")
    assert hits and "闰年" in hits[0]["content"], "提炼的教训应能被相似任务检索到"
    print("✅ 提炼的教训已入库,相似任务可检索到 → 经预检索注入,第二轮带着教训上场。")


if __name__ == "__main__":
    main()
