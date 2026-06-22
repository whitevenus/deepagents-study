"""
Ch3 切片:带「持久记忆 + 用户隔离 + 操作权限」的 worker。

演示三块产品地基(全在一个 CompositeBackend 里):
  1. /workspace/  → StateBackend   :临时草稿,任务结束即丢
  2. /memories/   → StoreBackend   :跨会话持久,按 user_id 隔离(= 数据权限雏形)
  3. FilesystemPermission           :禁止 agent 写 /policies/(= 操作权限雏形)

关键演示点:
  - 同一个 store,userA 和 userB 用不同 namespace → userA 的记忆 userB 看不到(行级隔离)。
  - userA 第二次会话仍能读回上次写的记忆(持久化)。

⚠️ 注意:namespace 只隔离 *agent 的虚拟文件系统*,不能替代业务层的 Casbin RBAC。

运行:
  uv run python -m agents.memory_agent
"""

from langgraph.store.memory import InMemoryStore

from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

from agents.first_agent import build_model  # 复用 Ch2 的模型选择逻辑


def build_agent(user_id: str, store: InMemoryStore):
    """为某个用户构建 worker。共享同一个 store,但 namespace 按 user_id 分区。"""
    backend = CompositeBackend(
        default=StateBackend(),  # 未匹配路由的路径 → 临时草稿
        routes={
            # /memories/ 下的文件存进持久 Store,且按当前 user_id 隔离
            "/memories/": StoreBackend(namespace=lambda rt: (user_id,)),
        },
    )
    return create_deep_agent(
        model=build_model(),
        backend=backend,
        store=store,
        # 操作权限:禁止 agent 写 /policies/ 下任何文件(具体规则放前面,first-match-wins)
        permissions=[
            FilesystemPermission(operations=["write"], paths=["/policies/**"], mode="deny"),
        ],
        system_prompt=(
            "你是一个有持久记忆的助手。"
            "需要长期记住的信息写到 /memories/ 目录;临时草稿写到 /workspace/。"
            "回答前先用 ls / read_file 查看 /memories/ 里有没有相关记忆。"
        ),
    )


def ask(agent, text: str) -> str:
    result = agent.invoke({"messages": [{"role": "user", "content": text}]})
    return result["messages"][-1].content


def demo():
    store = InMemoryStore()  # 一个共享 store,模拟生产里的持久层

    print("\n--- 用户A · 第1次会话:写入记忆 ---")
    agent_a1 = build_agent("user-A", store)
    print(ask(agent_a1, "请记住:我的名字是 venus,我偏好用 Python。把它写到 /memories/profile.md"))

    print("\n--- 用户A · 第2次会话(全新 agent 实例):应能读回记忆 ---")
    agent_a2 = build_agent("user-A", store)
    print(ask(agent_a2, "我叫什么名字?偏好什么语言?(查 /memories/)"))

    print("\n--- 用户B · 同一个 store:应看不到 A 的记忆(数据隔离) ---")
    agent_b = build_agent("user-B", store)
    print(ask(agent_b, "我叫什么名字?偏好什么语言?(查 /memories/,没有就直说不知道)"))


if __name__ == "__main__":
    demo()
