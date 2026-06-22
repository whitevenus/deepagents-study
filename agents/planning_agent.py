"""
Ch4 切片:任务规划,并把 agent 内部的 todo 清单抓出来。

核心目的:证明 todo 存在 *Agent State* 里(不是虚拟文件系统),
         并把这份结构化 todos 提取出来 —— 这就是未来渲染到看板 UI 的数据。

产品接缝:result["todos"] 里每一项 = 看板上一张卡片的一个子任务(subject + status)。
         status 三态 pending/in_progress/completed = 看板三列。

运行:
  uv run python -m agents.planning_agent
"""

import json

from deepagents import create_deep_agent

from agents.first_agent import build_model


PLANNER_PROMPT = """你是一位项目规划助手。
面对一个目标时,你会:
1. 先用 write_todos 把它拆成若干清晰的步骤(初始都设为 pending)
2. 把你认为应该"现在开始做"的第一步,状态更新为 in_progress
3. 最后用一两句话说明你的拆解思路
不需要联网,也不需要真正执行这些步骤,只做规划。
"""


def build_agent():
    # Ch4 只验证规划机制,不需要搜索工具 —— token 更省、验证更干净
    return create_deep_agent(
        model=build_model(),
        system_prompt=PLANNER_PROMPT,
    )


def render_board(todos: list) -> None:
    """把 agent 的 todos 按状态分列打印 —— 模拟看板三列的渲染。"""
    cols = {"pending": [], "in_progress": [], "completed": []}
    for t in todos or []:
        cols.setdefault(t.get("status", "pending"), []).append(t)
    label = {"pending": "📋 待办", "in_progress": "🔧 进行中", "completed": "✅ 已完成"}
    print("\n" + "=" * 18 + " 看板视图(从 agent state 提取) " + "=" * 18)
    for status in ["pending", "in_progress", "completed"]:
        print(f"\n【{label[status]}】")
        for t in cols.get(status, []):
            print(f"  - {t.get('subject') or t.get('content') or t}")
    print("=" * 64 + "\n")


def main():
    agent = build_agent()
    task = "帮我制定一个为期一周的「deepagents 入门学习计划」,拆成 5 个步骤。"
    result = agent.invoke({"messages": [{"role": "user", "content": task}]})

    # 关键:todos 就在返回的 state 里(由 TodoListMiddleware 注入,不在虚拟文件系统)
    print("\nstate 包含的字段:", list(result.keys()))
    todos = result.get("todos", [])
    print("\n原始 todos 数据(这就是要喂给看板 UI 的):")
    print(json.dumps(todos, ensure_ascii=False, indent=2))
    render_board(todos)

    print("=== 最终报告 ===\n")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
