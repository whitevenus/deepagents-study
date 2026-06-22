"""
Ch5 切片:协调者 + 专项子 agent,演示三大机制
  1. 上下文隔离:主 agent 用 task 委派,子 agent 在独立上下文干活
  2. 最小权限:子 agent 显式指定 tools=[](硬边界,没有别的工具可用)
  3. 结构化返回:子 agent 用 response_format 返回合法 JSON → 可直接落库

产品映射:协调者 = 接看板任务的 coordinator;summarizer = 一个专项 worker。
         主 agent 的 messages 很短(只看到摘要),子 agent 的中间过程被隔离掉了。

运行:
  uv run python -m agents.subagent_demo
"""

from pydantic import BaseModel, Field

from deepagents import create_deep_agent

from agents.first_agent import build_model, print_trace


class Summary(BaseModel):
    """子 agent 的结构化返回 —— 这就是能直接写进数据库的形状。"""
    points: list[str] = Field(description="3 条以内要点,每条不超过 25 字")
    sentiment: str = Field(description="整体情绪:positive / neutral / negative")


summarizer_subagent = {
    "name": "summarizer",
    # description 要具体:主 agent 靠它决定"何时派给谁"
    "description": "把一段文本压缩成要点并判断情绪。需要总结/提炼时使用。",
    # system_prompt 不继承主 agent,要独立写清,并规定输出
    "system_prompt": "你是总结专家。把用户给的文本压成不超过3条要点并判断情绪,只返回结论。",
    "tools": [],  # 最小权限:它不需要任何工具,显式清空 = 硬边界
    "response_format": Summary,  # 结构化返回:保证合法 JSON
}

COORDINATOR_PROMPT = """你是任务协调者。
你自己不要直接做总结。任何需要"总结/提炼文本"的活,必须用 task 工具委派给 summarizer 子 agent,
然后把它返回的结果转述给用户。保持你自己的上下文干净。
"""


def build_agent():
    return create_deep_agent(
        model=build_model(),
        subagents=[summarizer_subagent],
        system_prompt=COORDINATOR_PROMPT,
    )


def main():
    agent = build_agent()
    text = (
        "我们团队这周上线了看板的拖拽功能,用户反馈很积极,留存涨了 12%;"
        "但后台 agent 偶尔超时,需要下周优化任务队列。"
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": f"帮我总结这段话:{text}"}]}
    )

    print_trace(result["messages"])

    # 隔离的证据:主 agent 的 messages 很短 —— 子 agent 的中间过程不在这里
    print(f"主 agent 的 messages 条数: {len(result['messages'])}  (子 agent 的内部步骤被隔离,不在其中)")
    print("\n=== 协调者最终回复 ===\n")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
