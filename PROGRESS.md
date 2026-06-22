# PROGRESS — loop 外部记忆

> 每轮循环结束后在这里记:学了什么、写了什么代码、踩了什么坑、还有什么没搞懂。
> 下一轮开始前先读这里(解决"两次之间失忆")。

## 进度总览
- [ ] 准备篇 · AgentSeek CLI(上/下)  —— 可选,视是否用该脚手架而定
- [x] Ch1 · Agent Harness  ✅ verify 通过
- [x] Ch2 · 5分钟构建第一个 Agent  ✅ 跑通(带引用的研究报告)
- [x] Ch3 · 虚拟文件系统与上下文  ✅ 跑通(持久化+用户隔离已验证)
- [x] Ch4 · 任务规划与分解  ✅ 跑通(todos 在 state 中,已提取成看板数据)
- [x] Ch5 · 子 Agent 与上下文隔离  ✅ 跑通(委派+隔离+结构化返回)
- [ ] Ch6 · 异步子 Agent 并行编排
- [ ] Ch7 · Skills 可复用能力包
- [ ] Ch8 · 长期记忆与路由

---

## 轮次日志

### 轮 0 · 立项 (2026-06-22)
- 定方案:边学边建;UI 用 shadcn/ui + Tailwind(配合 Claude/Pencil 设计工具)。
- 落地 ROADMAP.md + PROGRESS.md。
- 已装依赖:deepagents, langchain-openai, tavily-python(项目名改为 deepagents-study)。
- 下一步:学 Ch1 Agent Harness。

### 轮 1 · Ch1 Agent Harness ✅ (2026-06-22)
- 要点:
  - 三层架构:Deep Agents(Harness 工具层) > LangChain(Framework 框架层) > LangGraph(Runtime 运行时);LangSmith 贯穿可观测。自底向上叠,不是替代。
  - Framework=锤子钉子(零件+agent循环,逻辑自写);Harness=装好的工具间(成熟模式开箱即用)。
  - 论点:成功 agent 产品都长得一样 → 文件系统/任务规划/子agent委派/上下文管理 是刚需 → harness 把它固化。= 现成的 loop engine。
  - 灵魂:Context Engineering。虚拟文件系统核心机制 = 按需读取而非全量塞 prompt;效果 = 防溢出/注意力稀释/能力退化。
  - 五大模块:文件系统 / 任务规划(write_todos) / 子agent委派(task) / 可插拔存储后端 / 长期记忆(LangGraph Memory Store)。
  - 选型:deepagents 模型无关(100+)+ 长期记忆,配 LangSmith = 企业级推荐。
- 代码切片:无(认知篇)。
- 遗留问题:无。
- verify:3 题自述全过(Framework/Harness 区别、虚拟文件系统为何存在、五大模块映射产品)。

### 轮 2 · Ch2 5分钟构建第一个 Agent (进行中)
- 要点:
  - 核心 API:create_deep_agent(model, tools, system_prompt) → agent.invoke({"messages":[...]});取 result["messages"][-1].content。
  - 只传自定义工具,harness 自动注入 文件系统/write_todos/task子agent/上下文管理。
  - 工具三要素:类型标注参数 + 返回类型 + docstring(agent 靠 docstring 决定何时用)。
  - 装的 deepagents 0.6.11 比课程多了 subagents/skills/memory/permissions/backend/store 参数 → 正好对应后续章节 + 产品需求。
  - 模型默认硅基流动免费 Qwen(兼容 OpenAI 接口);也可 "openai:gpt-4.1" / "anthropic:claude-sonnet-4-6"。
- 代码切片:agents/first_agent.py —— run_task(task)=「接任务→自动完成→返回结果」,worker 最小种子;.env.example 配置模板;已加 python-dotenv。
- 踩坑实录:
  1. key 填错(把 Tavily 的 tvly- 填进 SiliconFlow 格)→ 401。
  2. 7B 模型太弱,不会结构化 tool-calling → 输出乱码。换 nex-agi/Nex-N2-Pro 解决。= Ch1"模型是瓶颈"的活教材。
  3. 工具不一定被调:模型自判断"会答就不查"(按需调用)。问它不知道的问题才会真搜。
  4. 429 TPM 限流:include_raw_content=True 单次几万 token + 多轮 fan-out 撞穿每分钟限额。
     修法:internet_search 内强制节流(raw_content=False、max_results≤3)。
  5. 亲眼见到"结果太大自动存进虚拟文件系统"(Ch1 卸载长上下文的机制)+ LangSmith trace。
- verify:✅ 跑通,产出带官方文档引用的报告;LangSmith trace 确认 规划→多轮搜索→自我修正→综合。
  + 理解题 3 题全过(能力来自harness中间件 / 工具三要素+docstring作用 / 工具调用由模型决定+prompt可强制)。
  + 产品启发:关键校验步骤(如"必须跑测试")不能靠模型自觉,要 prompt 强制或做成固定流程(呼应 Ch1 verifier 是瓶颈)。

### 轮 3 · Ch3 虚拟文件系统与上下文管理 (进行中)
- 要点:
  - 六大文件工具:ls/read_file(分片+多模态)/write_file/edit_file/glob/grep。
  - 上下文自动管理:卸载(单次工具结果>20K token→存文件留预览)、总结(对话>85%窗口→摘要顶替,原文存文件)。
  - 可插拔后端:StateBackend(临时草稿)/FilesystemBackend(本地磁盘,危险)/LocalShellBackend(无隔离,禁用)/
    StoreBackend(跨会话持久+namespace按用户隔离)/CompositeBackend(按路径前缀路由)/沙箱(LangSmithSandbox等,安全执行)。
  - FilesystemPermission:声明式 allow/deny,first-match-wins,具体规则放前面。
  - 产品地基:namespace=数据隔离雏形、FilesystemPermission=操作权限雏形、持久Store=知识库、沙箱=安全执行。
- 关键决策(已写入 ROADMAP):两个权限平面(Casbin业务 vs deepagents文件系统)分开;agent跑代码必须沙箱非普通Docker。
- verify:理解题 3 题全过(卸载vs总结触发条件 / namespace实现用户隔离及其局限 / 为何必须沙箱)。
- 代码切片:agents/memory_agent.py —— CompositeBackend(/workspace→State 临时,/memories→Store 按 user_id 隔离)+ FilesystemPermission 禁写 /policies/。
- verify:✅ demo 跑通,LangSmith trace 坐实:A写→A新实例读回(持久化)→B同store读到空(namespace隔离)。
- 关键认知:/memories 是虚拟路径,在 InMemoryStore(RAM),OS 的 ls 找不到正常;进程退出即丢。
- 生产含义:InMemoryStore 仅开发用;产品要"知识库沉淀"须换持久化 Store(部署 LangSmith 自动配 / 自托管接 Postgres)。换 store 一行即可。
- 遗留问题:无。

### 轮 4 · Ch4 任务规划与分解 ✅ (2026-06-22)
- 要点:
  - write_todos 解决:漏步骤/重复劳动/半途而废/质量飘忽。
  - todo 结构 {content, status},三态 pending→in_progress→completed = 看板三列。
  - **todo 存在 Agent State 独立字段(不是虚拟文件系统!)**,TodoListMiddleware 维护。
  - 北极星机制:① todo 在 state,Summarization 只压 messages 碰不到;② 每步把当前 todo 重注入系统提示。
  - 子 agent 看不到主 agent 的 todo(Ch5 伏笔)。多步规划需 SOTA 模型。
- 产品接缝:result["todos"] = 喂看板的数据;实时性靠 LangGraph streaming + checkpointer。
- 代码切片:agents/planning_agent.py —— 纯规划 → 从 state 提取 todos → 三列渲染。
- 踩坑:多步+搜索+报告 → 429 TPM(模型烧token)。修法:① first_agent 全局加 InMemoryRateLimiter(0.5 req/s);② 改纯规划去搜索。
- API 细节:文档 todo 字段=subject,实际 0.6.11=content。以实跑为准。
- verify:✅ state 含 todos,看板渲染正确(1 in_progress+4 pending)。理解题 Q2 误区(以为存FS)已纠正。

### 轮 5 · Ch5 子 Agent 与上下文隔离 ✅ (2026-06-22)
- 要点:
  - task 工具委派子任务给独立子 agent;子 agent 独立上下文执行,只回最终结果。
  - 上下文隔离(项目经理/专项负责人比喻):省上下文+省钱+主agent专注;子agent看不到主agent的todo。
  - 字典定义:name(必填)/description(必填,主agent靠它路由)/system_prompt(必填,不继承)/tools(默认继承,显式则完全替换)/model/response_format/permissions。
  - 三机制:① 隔离(task委派+强制精简返回)② 最小权限(显式tools=硬边界)③ 结构化返回(response_format+Pydantic→合法JSON可落库)。
  - 内置 general-purpose 子agent:唯一继承主agent全部能力,纯做隔离。
  - 最佳实践:description具体/prompt规定输出格式字数/工具精简/不同子agent配不同模型/返回精简。
- 产品映射:coordinator→data-collector→analyzer→writer 管线 = 看板任务执行管线。
- 代码切片:agents/subagent_demo.py —— coordinator + summarizer 子agent(tools=[],response_format=Summary)。
- API 细节:task 参数实际叫 subagent_type(非文档的 name)。
- verify:✅ 轨迹有 task(subagent_type=summarizer),返回结构化JSON,主agent messages仅4条(隔离证实)。理解题Q1Q2过,Q3机制映射已补齐。

---

## 📍 下次从这里继续(2026-06-22 收工)
- 进度:**5/8**,Ch1-5 ✅。基础(harness/agent/虚拟FS/规划/子agent)全部跑通。
- 全局基础设施已就位:.env 多provider切换 + InMemoryRateLimiter 限流(0.5 req/s)+ internet_search 节流。
- 当前模型:nex-agi/Nex-N2-Pro(SiliconFlow)。免费档 TPM 偏低,重任务仍可能 429。
- 已有代码切片:agents/{first_agent, memory_agent, planning_agent, subagent_demo}.py
- **下一步:Ch6《异步子 Agent 并行编排》** —— 多 agent 并发接任务,对应产品后台并发处理 + Phase 2。
- 复习入口:直接说"继续/进 Ch6"即可;ROADMAP.md 是总蓝图,本文件是进度记忆。

### 轮 6 · Ch6 异步子 Agent 并行编排 (待开始)
- 要点:
- 代码切片:
- verify:
