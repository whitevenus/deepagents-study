# ROADMAP — Agent-Jira / AutoBoard

> 用 **Loop Engineering** 的方式,以 deepagents-in-action 课程为主、结合网上资料,
> 边学边建一个企业级「Agent 驱动的看板」生产项目。
> 本文件是 loop 的总 `/goal` 看板;每轮循环的笔记/遗留问题记在 `PROGRESS.md`。

## 一句话目标
一个看板:人发任务 → 后台 deepagents 自动接单、拆解、执行、测试、交付;
带权限(操作+数据)、知识库沉淀、审计日志、agent 自我进化。

## 技术栈
- 前端:**React + shadcn/ui + Tailwind**(可与 Claude / Pencil 设计工具配合);看板拖拽用 dnd-kit
- 后端:**FastAPI**
- Agent 运行时:**deepagents**(底层 LangGraph)
- 数据库:**PostgreSQL + pgvector**(业务数据 + 知识库向量)
- 权限:**Casbin (pycasbin)** —— RBAC(操作权限)+ ABAC(数据/行级权限)
- 任务队列:Celery 或 LangGraph async worker
- 可观测/审计:结构化日志 + LangSmith(agent 轨迹)
- LLM:可插拔(langchain-openai 已装,也可接 Claude)

## 学习策略:边学边建
逐章学,每章 demo 直接做成产品的真实垂直切片,不写一次性代码。

## 课程章节 ↔ 产品能力 映射
| # | 章节 | 地址 | 对应产品切片 |
|---|------|------|------|
| 准备 | AgentSeek CLI(上) | /chapters/pre01-agentseek-create/ | 项目脚手架(可选) |
| 准备 | AgentSeek CLI(下) | /chapters/pre02-agentseek-skills/ | 开发技能安装(可选) |
| 1 | Agent Harness | /chapters/ch01-agent-harness/ | worker 主循环骨架 |
| 2 | 5分钟构建第一个 Agent | /chapters/ch02-quickstart/ | 单 agent 接单执行的最小闭环 |
| 3 | 虚拟文件系统与上下文 | /chapters/ch03-virtual-filesystem/ | 任务工作区 + 产物落库 |
| 4 | 任务规划与分解 | /chapters/ch04-task-planning/ | task → subtask 拆解 |
| 5 | 子 Agent 与上下文隔离 | /chapters/ch05-subagents/ | 数据权限边界 |
| 6 | 异步子 Agent 并行编排 | /chapters/ch06-async-subagents/ | 多 agent 并发接单 + 任务队列 |
| 7 | Skills 可复用能力包 | /chapters/ch07-skills/ | agent 技能(写码/测试/检索) |
| 8 | 长期记忆与路由 | /chapters/ch08-long-term-memory/ | 知识库沉淀 + 任务路由 |

(地址前缀:https://datawhalechina.github.io/deepagents-in-action)

## 分阶段路线图(每阶段终止条件 = 该 loop 的可测试 /goal)
- **Phase 0 · 边学边搭(对应 8 章)** —— ✅ 8 章都有「能跑的切片 + 能用自己的话讲清机制」
- **Phase 1 · MVP 闭环** —— ✅ 建任务 → agent 自动完成 → 看板显示结果,端到端跑通
- **Phase 2 · 多 agent 异步编排** —— ✅ 同发 5 个任务并发完成无串扰
- **Phase 3 · 权限系统(Casbin)** —— ✅ 越权被拒,权限矩阵单测通过
- **Phase 4 · 知识库沉淀(pgvector + 长期记忆)** —— ✅ 相似任务第二次更快/更准(固定基准)
- **Phase 5 · 审计日志(两层设计)** —— ✅ 任一任务可完整追溯 谁/哪个agent/做了什么/何时
  - 第一层 可观测性:Langfuse(开源自托管,优于 LangSmith 云版——数据不出境)记 agent 每步推理/工具调用,经 LangChain callback / OpenTelemetry 接入。
  - 第二层 业务审计:自建 Postgres audit_log 表(append-only 不可篡改),记 谁/哪个agent/动作/对象/前后值/时间/trace_id。
  - 打通:audit_log 每条存 trace_id → UI 里从"做了什么"一键跳到 Langfuse 看"为什么"。
  - 埋点位置:用自定义 deepagents **middleware**(同 FilesystemMiddleware/SubAgentMiddleware 那一层)拦截每次工具调用/数据变更,自动写 audit_log。Ch1 强调的中间件机制 = 审计/权限的天然拦截点。
- **Phase 6 · 自我进化(反思循环)** —— ✅ 故意会失败的任务,第二轮因吸取教训而成功
- **Phase 7 · 生产化** —— Docker compose、配置/密钥、错误恢复、限流、监控

## 两个关键架构决策(Ch3 衍生,务必记住)
1. **两个独立权限平面,别混**:
   - 业务数据权限(谁能看/改哪条任务/项目)= Casbin(RBAC+ABAC)在 FastAPI/DB 层,查 Postgres 行。
   - Agent 文件系统权限(agent 虚拟FS能读写什么)= deepagents 的 namespace 隔离 + FilesystemPermission。
   - namespace 只隔离 agent 自己的文件/记忆,**不能替代** Casbin 管业务数据访问。两套都要。
2. **agent 跑代码必须用沙箱,不是普通 Docker**:
   - 普通 Docker 共享内核,跑不可信代码隔离不够。
   - 生产级:gVisor / Kata / Firecracker microVM;或托管服务 E2B / Modal / Daytona / Runloop。
   - deepagents 自带 LangSmithSandbox,可插拔 backend → 到时换一行即可。
   - 学习/本地阶段先用 Docker 容器够用;生产再换托管沙箱。Mac 虚拟化只用于本地开发。

## "自我进化"的务实定义
反思循环:任务完成 → 评审 agent 抽取"教训" → 写成可复用 Skill/记忆存入知识库
→ 路由器按历史成功率选更优 Skill/prompt → (进阶)prompt/skill 版本化 + 成功率 A/B。

## 参考开源项目
- makeplane/plane — 开源 Jira(看板 UI + 任务数据模型)
- casbin/casbin — 操作权限 + 数据权限
- langchain-ai/deepagents — 框架本体 + 示例
- pgvector/pgvector — 向量检索

## loop 怎么跑
每轮:挑下一个切片 → 学对应章节(官网+补充资料)→ 写代码 → 跑测试验证 → 写回 PROGRESS.md。
Claude Code 当 loop 引擎,你当 verifier(判断 懂没懂 / 对没对)。
