"""可观测层:把 agent 每步推理/工具调用送进 Langfuse(自托管开源,不用 LangSmith 云)。

设计:env-gated + best-effort——没配 Langfuse(LANGFUSE_PUBLIC_KEY/SECRET_KEY)就全程 no-op,
任何 Langfuse 侧错误都不许拖垮任务执行(同知识库 is_pg、_remember 的护栏思路)。

串联:worker 先 new_trace_id() 生成一个 trace_id,既塞进 agent 的 invoke config(让 Langfuse
用这个 id 建 trace),又写进 audit_log——于是审计里「做了什么」能一键跳 Langfuse 看「为什么」。
"""

import os
import uuid


def enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def new_trace_id() -> str | None:
    """生成一个 Langfuse 兼容的 trace id;没配 Langfuse 时返回 None。
    用 SDK 的 create_trace_id 保证格式合法(32 位小写 hex),取不到再退化成 uuid。"""
    if not enabled():
        return None
    try:
        from langfuse import get_client

        return get_client().create_trace_id()
    except Exception:  # noqa: BLE001
        return uuid.uuid4().hex


def trace_config(trace_id: str | None, user_id: str | None = None) -> dict:
    """构造传给 agent.invoke 的 config:挂 Langfuse callback,并用 trace_context 绑定我们的 trace_id
    (v4 SDK:CallbackHandler(trace_context=...) 让这次执行的轨迹落在这个 id 下,与审计串联)。
    没配 / 出错 → 返回 {}(等价于不加 callback),绝不影响 agent 执行。"""
    if not (trace_id and enabled()):
        return {}
    try:
        from langfuse.langchain import CallbackHandler

        cfg: dict = {"callbacks": [CallbackHandler(trace_context={"trace_id": trace_id})]}
        if user_id:
            cfg["metadata"] = {"langfuse_user_id": user_id}
        return cfg
    except Exception:  # noqa: BLE001  Langfuse 没装/初始化失败 → 退化成无 trace
        return {}
