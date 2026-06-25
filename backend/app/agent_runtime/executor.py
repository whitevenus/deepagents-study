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


def _make_kb_tool(owner_id: str | None):
    """构造按 owner 隔离的知识库检索工具(闭包捕获 owner_id,只检索该用户的知识,不跨用户泄漏)。"""

    def search_knowledge_base(query: str) -> str:
        """检索知识库,找与查询最相关的历史任务经验/结论。
        遇到可能有可复用过往经验的任务时,先用它查一下,别重复劳动。

        Args:
            query: 用自然语言描述你想查的主题或问题。

        Returns:
            最相关的若干条历史知识(带相似度);无相关内容时明确告知。
        """
        from app.knowledge.store import search_knowledge

        hits = search_knowledge(query, k=3, owner_id=owner_id)
        if not hits:
            return "知识库暂无相关内容。"
        return "\n\n".join(f"[相似度 {h['score']:.2f}] {h['content']}" for h in hits)

    return search_knowledge_base


# 预检索注入的相似度阈值:只把够相关的历史经验塞进 prompt,避免注入噪声。
# ponytail: 这是个校准旋钮——eval 里相关 0.78、无关 0.33,0.6 能干净分开;模型/数据变了再调。
_KB_INJECT_THRESHOLD = float(os.getenv("KB_INJECT_THRESHOLD", "0.6"))


def run_task(title: str, description: str, owner_id: str | None = None) -> str:
    """同步执行一个任务,返回结果文本。供后台任务调用。owner_id 用于知识库按用户隔离检索。"""
    from app.knowledge.store import search_knowledge

    # 预检索注入(retrieve-then-generate):开跑前先查知识库,命中够高的直接进 system prompt。
    # 把「有没有查知识库」从模型自由裁量变成固定流程——别靠模型自觉(Ch1/Ch8 反复踩过的坑)。
    hits = search_knowledge(f"{title} {description}", k=3, owner_id=owner_id)
    context = "\n".join(f"- {h['content']}" for h in hits if h["score"] >= _KB_INJECT_THRESHOLD)

    system_prompt = "你是任务执行助手。根据任务标题和描述完成它,给出清晰、可交付的结果。"
    if context:
        system_prompt += "\n\n以下是知识库中可复用的历史经验,请参考并融入你的结果:\n" + context
    # 保留工具:需要更多/更具体的历史经验时,模型可主动再查(预检索打底 + 工具补查)。
    system_prompt += "\n\n如需补充更多历史经验,可调用 search_knowledge_base 检索。"

    agent = create_deep_agent(
        model=_build_model(),
        tools=[_make_kb_tool(owner_id)],
        system_prompt=system_prompt,
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


class _Reflection(BaseModel):
    adequate: bool = Field(description="结果是否真正、充分地完成了任务(失败信息一律 false)")
    reusable: bool = Field(
        description="是否有「非显然、对未来同类任务可复用」的教训值得存进知识库。要吝啬:"
        "只有任务失败/不达标、或踩到不显然的坑/有非平凡洞见时才 true;普通顺利完成的常规任务一律 false。"
    )
    lesson: str = Field(
        description="一条 ≤2 句、面向未来、可复用的经验:不达标/失败就说清问题出在哪、下次怎么做;达标就提炼做好这类任务的关键点。reusable=false 时可留空"
    )


def reflect(title: str, description: str, result: str, status: str = "done") -> dict:
    """复盘:裁判结果是否达标 + 是否值得沉淀 + 提炼一条可复用教训(自我进化核心,Phase 6)。
    ponytail: 单次 LLM 调用同时出 {达标, 值不值得存, 教训};reusable 是存储闸,挡掉
    「答得好好的常规任务」那种正确的废话教训,避免污染知识库。裁判本身是 LLM(不完美 = verifier
    瓶颈),更严的多视角投票/人工反馈评判留到企业级阶段。"""
    model = _structured_model().with_structured_output(_Reflection)
    prompt = (
        "你是任务复盘助手。给定任务和它的执行结果(或失败信息):"
        "① 判断结果是否充分正确地完成了任务;"
        "② 判断是否有「非显然、对未来同类任务可复用」的教训值得记下来(要吝啬,普通顺利完成的常规任务不值得记);"
        "③ 若值得,提炼一条可复用的经验/教训。\n"
        f"任务标题:{title}\n任务描述:{description or '(无)'}\n"
        f"执行状态:{status}\n执行结果:{result}"
    )
    r = model.invoke(prompt)
    return {"adequate": r.adequate, "reusable": r.reusable, "lesson": r.lesson}


def decompose(title: str, description: str) -> list[dict]:
    """把一个大任务拆成 2-5 个可独立执行的子任务(结构化输出,直接用模型不走 deep agent)。"""
    model = _structured_model().with_structured_output(_Plan)
    prompt = (
        "把下面的任务拆解成 2-5 个可以独立执行的子任务,每个有清晰的标题和说明。\n"
        f"任务:{title}\n描述:{description or '(无)'}"
    )
    plan = model.invoke(prompt)
    return [{"title": s.title, "description": s.description} for s in plan.subtasks]
