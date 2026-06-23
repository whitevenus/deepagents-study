"""
Ch7 切片:挂载一个真实的 Skill(task-triage),看 agent 按需激活并照着干。

Skill 位置:ch07_skills/skills/task-triage/SKILL.md
  - backend root_dir 指向 ch07_skills/(专用目录,不暴露项目根的 .env)
  - skills=["/skills/"] 相对 root_dir 解析

验证点:
  - 给一个"triage 任务"的请求 → agent 应激活 task-triage skill,
    按 SKILL.md 规定的格式输出(类型/优先级/预估/理由)。
  - 渐进式披露:启动时只加载 skill 的 description,匹配后才加载正文。

运行:
  uv run python -m agents.skill_agent
"""

import os

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from agents.first_agent import build_model

# Skill 所在的根目录(专用沙箱目录,避免 FilesystemBackend 读到项目根的 .env)
SKILLS_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ch07_skills")


def build_agent():
    backend = FilesystemBackend(root_dir=SKILLS_ROOT, virtual_mode=True)
    return create_deep_agent(
        model=build_model(),
        backend=backend,
        skills=["/skills/"],  # 相对 root_dir → ch07_skills/skills/
        system_prompt="你是研发助手。遇到合适的任务时,使用已加载的 skill 来规范你的处理流程。",
    )


def main():
    agent = build_agent()
    task = "帮我 triage 这个任务:用户反馈登录页在 Safari 上偶发白屏,刷新后正常。"
    result = agent.invoke({"messages": [{"role": "user", "content": task}]})
    print("\n=== agent 输出(应符合 task-triage skill 规定的格式)===\n")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
