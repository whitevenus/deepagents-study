"""
Ch2 切片:第一个 Deep Agent —— 一个带联网搜索的研究助手。

为什么写成 run_task(task) 的形态?
  这就是未来产品里「后台 agent 接一个任务 → 自动完成 → 返回结果」的最小种子。
  Phase 1 做 MVP 时,worker 接到看板上的任务,本质就是调用这个 run_task()。

运行:
  1. cp .env.example .env  并填入 SILICONFLOW_API_KEY(或 OPENAI/ANTHROPIC)+ TAVILY_API_KEY
  2. uv run python -m agents.first_agent
  3. 或:uv run python -m agents.first_agent "你想研究的问题"
"""

import os
import sys
from typing import Literal

from dotenv import load_dotenv
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_openai import ChatOpenAI
from tavily import TavilyClient

from deepagents import create_deep_agent

load_dotenv()

# 客户端限流器:主动放慢模型请求节奏,避免撞穿 SiliconFlow 等服务商的 TPM(每分钟token)限额。
# requests_per_second=0.5 → 平均每 2 秒最多 1 次模型请求。免费档够用;以后换高档可调大。
_rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.5,
    check_every_n_seconds=0.1,
    max_bucket_size=2,
)


def build_model():
    """按 .env 里的 LLM_PROVIDER 选择模型。默认硅基流动(免费模型,先跑通)。"""
    provider = os.environ.get("LLM_PROVIDER", "siliconflow").lower()

    if provider == "siliconflow":
        return ChatOpenAI(
            model=os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct"),
            api_key=os.environ["SILICONFLOW_API_KEY"],
            base_url="https://api.siliconflow.cn/v1",
            rate_limiter=_rate_limiter,
        )
    if provider == "openai":
        # create_deep_agent 也接受 "openai:gpt-4.1" 字符串,这里返回实例更灵活
        return ChatOpenAI(model=os.environ.get("MODEL_NAME", "gpt-4.1"), rate_limiter=_rate_limiter)
    if provider == "anthropic":
        # 直连 Claude:用字符串形式让 deepagents 自己构建
        return f"anthropic:{os.environ.get('MODEL_NAME', 'claude-sonnet-4-6')}"
    raise ValueError(f"未知 LLM_PROVIDER: {provider}")


# ---- 自定义工具:联网搜索(工具三要素:类型标注 + 返回类型 + docstring)----
_tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> dict:
    """联网搜索给定查询并返回结果。

    Args:
        query: 搜索关键词。
        max_results: 返回结果数量上限。
        topic: 搜索领域分类。
        include_raw_content: 是否包含网页原文。
    """
    # 节流:不管模型要多少,都压下来,避免撞穿 SiliconFlow 的 TPM(每分钟token)限额。
    # 原始网页全文(raw_content)是 token 大户,直接关掉;条数也封顶。
    max_results = min(max_results, 3)
    return _tavily.search(
        query,
        max_results=max_results,
        include_raw_content=False,  # 强制关闭:抓全文会瞬间几万 token
        topic=topic,
    )


RESEARCH_INSTRUCTIONS = """你是一位专业的研究员。
你的工作是进行深入研究,然后撰写一份结构清晰的研究报告(用中文)。

你可以使用 internet_search 工具搜索互联网获取信息。
请先规划要点,再逐项检索,最后综合成报告。
"""


def build_agent():
    """构建研究 agent。注意:只传了 1 个工具,文件系统/任务规划/子agent 由 harness 自动注入。"""
    return create_deep_agent(
        model=build_model(),
        tools=[internet_search],
        system_prompt=RESEARCH_INSTRUCTIONS,
    )


def print_trace(messages: list) -> None:
    """打印 agent 内部轨迹:每一步调了什么工具、传了什么参数。verify 用。"""
    print("\n" + "=" * 20 + " 内部轨迹 " + "=" * 20)
    for m in messages:
        role = m.__class__.__name__
        tool_calls = getattr(m, "tool_calls", None)
        if tool_calls:  # AIMessage 发起的工具调用
            for tc in tool_calls:
                print(f"  🔧 调用工具: {tc['name']}  参数={tc.get('args', {})}")
        elif role == "ToolMessage":  # 工具返回结果
            content = str(getattr(m, "content", ""))
            name = getattr(m, "name", "?")
            print(f"  📥 工具[{name}]返回: {content[:120]}{'...' if len(content) > 120 else ''}")
    print("=" * 52 + "\n")


def run_task(task: str, verbose: bool = False) -> str:
    """接一个任务 → agent 自动完成 → 返回最终文本。(产品里 worker 的最小原型)"""
    agent = build_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": task}]})
    if verbose:
        print_trace(result["messages"])
    return result["messages"][-1].content


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "什么是 LangGraph?"
    print(f"\n=== 任务: {task} ===\n")
    answer = run_task(task, verbose=True)
    print("\n=== 最终回答 ===\n")
    print(answer)
