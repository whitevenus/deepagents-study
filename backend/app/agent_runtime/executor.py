"""产品的 agent 执行器:把一个看板任务交给 deepagents 完成,返回结果文本。

刻意保持干净独立(不 import learning/ 的学习 demo)。
MVP 阶段 agent 只做"理解任务 → 给出结果文本",不写代码不跑测试(那要沙箱,Phase 2+)。
"""

import os

from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from deepagents import create_deep_agent

# 客户端限流,避免撞 SiliconFlow 等服务商的 TPM 限额(沿用学习阶段验证过的做法)。
_rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.5, check_every_n_seconds=0.1, max_bucket_size=2
)


# 单次 LLM 请求超时(秒)。Phase 1 的卡死 bug 根因:ChatOpenAI 默认无 timeout,
# 模型挂起 → 任务永久 in_progress。设得比 worker 的 TASK_TIMEOUT 小,让卡住的线程能自己退出。
_LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))


def _build_model():
    provider = os.getenv("LLM_PROVIDER", "siliconflow").lower()
    if provider == "siliconflow":
        return ChatOpenAI(
            model=os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct"),
            api_key=os.environ["SILICONFLOW_API_KEY"],
            base_url="https://api.siliconflow.cn/v1",
            rate_limiter=_rate_limiter,
            timeout=_LLM_TIMEOUT,
        )
    if provider == "openai":
        return ChatOpenAI(
            model=os.getenv("MODEL_NAME", "gpt-4.1"), rate_limiter=_rate_limiter, timeout=_LLM_TIMEOUT
        )
    return f"anthropic:{os.getenv('MODEL_NAME', 'claude-sonnet-4-6')}"


def run_task(title: str, description: str) -> str:
    """同步执行一个任务,返回结果文本。供后台任务调用。"""
    agent = create_deep_agent(
        model=_build_model(),
        system_prompt="你是任务执行助手。根据任务标题和描述完成它,给出清晰、可交付的结果。",
    )
    prompt = f"任务:{title}\n描述:{description}\n\n请完成这个任务并给出结果。"
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    return result["messages"][-1].content


class _Subtask(BaseModel):
    title: str = Field(description="子任务标题,简短")
    description: str = Field(description="子任务的具体说明")


class _Plan(BaseModel):
    subtasks: list[_Subtask] = Field(description="2-5 个可独立执行的子任务")


def _structured_model():
    m = _build_model()
    if isinstance(m, str):  # anthropic 分支返回的是字符串,转成真模型实例
        from langchain.chat_models import init_chat_model

        return init_chat_model(m, rate_limiter=_rate_limiter)
    return m


def decompose(title: str, description: str) -> list[dict]:
    """把一个大任务拆成 2-5 个可独立执行的子任务(结构化输出,直接用模型不走 deep agent)。"""
    model = _structured_model().with_structured_output(_Plan)
    prompt = (
        "把下面的任务拆解成 2-5 个可以独立执行的子任务,每个有清晰的标题和说明。\n"
        f"任务:{title}\n描述:{description or '(无)'}"
    )
    plan = model.invoke(prompt)
    return [{"title": s.title, "description": s.description} for s in plan.subtasks]
