"""
Ch8 收官切片:长期记忆 + AGENTS.md 自更新 + 跨会话持久。
串起 Ch3(StoreBackend/namespace)+ Ch7(skills/memory 都是文件)+ Ch8(memory= 启动加载)。

演示"自我进化"最小闭环:
  1. 预填 AGENTS.md(一条回答风格规范)→ memory= 启动自动加载
  2. 会话1:agent 遵循该风格;然后被要求把一条新规范写进 AGENTS.md(自更新)
  3. 会话2(全新 agent 实例,同一 store):启动自动加载更新后的 AGENTS.md → 行为已进化

运行:
  uv run python -m agents.memory_capstone
"""

from langgraph.store.memory import InMemoryStore

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data

from agents.first_agent import build_model

USER_ID = "user-venus"
AGENTS_PATH = "/memories/AGENTS.md"


def build_agent(store: InMemoryStore):
    backend = CompositeBackend(
        default=StateBackend(),
        routes={"/memories/": StoreBackend(namespace=lambda rt: (USER_ID,))},
    )
    return create_deep_agent(
        model=build_model(),
        backend=backend,
        store=store,
        memory=[AGENTS_PATH],  # 启动时把 AGENTS.md 内容注入系统提示
        system_prompt="你是助手。严格遵守你长期记忆 AGENTS.md 里的行为准则。",
    )


def ask(agent, text: str) -> str:
    r = agent.invoke({"messages": [{"role": "user", "content": text}]})
    return r["messages"][-1].content


def main():
    store = InMemoryStore()

    # 预填 AGENTS.md(初始行为准则)—— 模拟"已有的长期记忆"
    store.put(
        (USER_ID,),
        AGENTS_PATH,
        create_file_data("## 回答风格\n- 回答务必简洁,不超过 3 句话。\n"),
    )

    print("\n--- 会话1:遵循初始 AGENTS.md(应简洁≤3句)---")
    a1 = build_agent(store)
    print(ask(a1, "什么是 Python?"))

    print("\n--- 会话1:要求 agent 把新准则写进长期记忆 ---")
    print(ask(a1, "请把这条加入你的长期记忆 AGENTS.md:以后每次回答都以 '✅ ' 开头。用 edit_file 更新它。"))

    print("\n--- 会话2:全新 agent 实例,同一 store,启动加载进化后的 AGENTS.md ---")
    a2 = build_agent(store)
    print(ask(a2, "什么是 LangChain?"))  # 应同时:简洁 + 以 ✅ 开头

    print("\n--- 当前 AGENTS.md 内容(已被 agent 自更新)---")
    item = store.get((USER_ID,), AGENTS_PATH)
    print(item.value if item else "(空)")


if __name__ == "__main__":
    main()
