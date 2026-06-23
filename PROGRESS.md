# PROGRESS — loop 外部记忆

> 每轮循环结束后在这里记:学了什么、写了什么代码、踩了什么坑、还有什么没搞懂。
> 下一轮开始前先读这里(解决"两次之间失忆")。

## 🔄 新会话恢复指南(给下次开新会话的你/Claude)
- **现状**:Phase 0(deepagents 8 章全学完)+ Phase 1(MVP 闭环)均已完成。
- **起服务**:
  - 后端:`uv run uvicorn app.main:app --app-dir backend --port 8000 --reload`
  - 前端:`cd frontend && pnpm dev` → 开 http://127.0.0.1:5173
  - 跑前先 `cp .env.example .env` 填 key(备份在 `learning/bak.txt`,已 gitignore)
- **代码地图**:
  - `backend/app/` —— FastAPI:`tasks/`(看板任务领域)+ `agent_runtime/executor.py`(agent 执行器)
  - `frontend/` —— React+Vite+Tailwind 看板
  - `learning/` —— 学 deepagents 的过程产物(已 gitignore,本地保留,产品不依赖)
  - `references/fastapi-best-architecture/` —— FBA 借鉴蓝图(已 gitignore)
- **下一步 = Phase 2 · 多 agent 异步并发**(对应 Ch6 动手):直接说"开始 Phase 2"。
- **关键决策备忘**(详见 ROADMAP.md):极简优先 / React+shadcn 自建 / 借鉴 FBA 后端蓝图 / ponytail 防过度设计 / 主键 UUID / 两个权限平面(Casbin业务 vs deepagents文件系统)/ agent 跑代码必须沙箱 / deepagents 无向量检索需自接 pgvector。

## 进度总览
- [ ] 准备篇 · AgentSeek CLI(上/下)  —— 可选,视是否用该脚手架而定
- [x] Ch1 · Agent Harness  ✅ verify 通过
- [x] Ch2 · 5分钟构建第一个 Agent  ✅ 跑通(带引用的研究报告)
- [x] Ch3 · 虚拟文件系统与上下文  ✅ 跑通(持久化+用户隔离已验证)
- [x] Ch4 · 任务规划与分解  ✅ 跑通(todos 在 state 中,已提取成看板数据)
- [x] Ch5 · 子 Agent 与上下文隔离  ✅ 跑通(委派+隔离+结构化返回)
- [x] Ch6 · 异步子 Agent 并行编排  ✅ (认知章,动手并入 Phase 2)
- [x] Ch7 · Skills 可复用能力包  ✅ 跑通(skill 按需激活+格式固化)
- [x] Ch8 · 长期记忆与路由  ✅ 跑通(自更新+持久机制验证;模型服从性是另一回事)

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

### 轮 6 · Ch6 异步子 Agent 并行编排 ✅ (2026-06-23,认知章)
- 要点:
  - 同步瓶颈:主agent调task期间被阻塞;长任务"死机"、中途不能追加/取消。
  - 判定法则:子任务<5s用同步;数分钟以上且需交互用异步。
  - AsyncSubAgent:name/description/graph_id(需在langgraph.json注册)/url(不填走ASGI进程内,填了走HTTP远程)。
  - 5个遥控器工具:start/check/update/cancel/list_async_task(自动注入)。task ID=thread ID。
  - async_tasks state channel:元数据独立存,不随消息压缩丢失(同 Ch4 todos 设计思路)。
  - 工程:每run占1 worker槽(1主+3子=4槽,--n-jobs-per-worker);起步单部署ASGI,按需拆HTTP。
  - 坑:别start完立刻check;报进度前先check/list(对话状态永远过时);task_id不截断。
- 关键纠正:并发 ≠ 必须拆HTTP。并发靠worker槽位数,单体ASGI起步即可;拆HTTP是为资源/团队边界,不是并发本身。
- 产品映射:异步子agent=后台worker;5工具=任务调度API;async_tasks=任务队列状态;ASGI→HTTP=单体→微服务演进。
- 动手:延后到 Phase 2(需起 langgraph dev 部署服务,届时随后端一起做)。
- verify:✅ 口述,Q1(同步异步判定+产品场景)Q2(channel设计同todos)满分;Q3(误以为并发须拆HTTP)已纠正。

### 轮 7 · Ch7 Skills 可复用能力包 ✅ (2026-06-23)
- 要点:
  - 能力三角:Skills(按需加载的领域workflow)/Memory(启动加载的持久上下文/AGENTS.md)/Tools(原子操作)。
  - 决策口诀:所有对话都要→Memory;特定任务专业流程→Skills;原子动作→Tools。
  - Skill 结构:目录 + SKILL.md(YAML frontmatter:name必须=目录名、description=选用唯一依据;Markdown正文)+ 可选 scripts/references/assets。
  - 渐进式披露三级:L1 启动只加载name+desc(几百token)/L2 匹配激活才加载正文/L3 引用时LLM自取附件。→ 50个skill也不爆。
  - skills参数:路径列表,相对backend根,多路径last-wins。存哪取决于backend(Filesystem/State/Store)。
  - 治理:FilesystemPermission 对 /skills/** deny(只读)或 interrupt(审批);分层shared(只读)+personal(可写)。
  - 开放标准 agentskills.io,30+工具采纳(含Claude Code自身);跨框架复用,"like npm for agents"。
- 自我进化(业界做法):① 反思→沉淀Skill/Memory(主流,=Phase6)② 成功案例检索few-shot ③ prompt/skill A/B优化 ④ 轨迹微调(罕见)。关键:人工审批+去重版本化,verifier是瓶颈。
- 产品映射:agent能力(code-review/testing/检索)做成Skill按角色加载;自我进化=把经验沉淀成Skill写进StoreBackend(namespace分层)+interrupt审批防污染。
- 代码切片:ch07_skills/skills/task-triage/SKILL.md + agents/skill_agent.py(FilesystemBackend专用root避开.env)。
- verify:✅ 跑通,agent精准激活skill,严格按"类型/优先级/预估/理由"格式输出(bug/P1/M)。理解题3题全过。

### 轮 8 · Ch8 长期记忆与路由 ✅ (2026-06-23)
- 要点:
  - 短期记忆=Checkpointer(单thread内State,thread_id是边界);长期记忆=StoreBackend(跨thread)+memory=参数(启动加载,靠namespace隔离不受thread_id影响)。
  - 三级namespace:user(个人偏好,隔离)/assistant(agent知识,共享)/org(组织策略,只读)。
  - memory=参数:列的文件启动时自动注入系统提示;AGENTS.md=agent从反馈学到的改进指令(自我进化载体)。
  - "路由"=backend路由(按路径前缀选后端),不是任务/检索路由。
  - **deepagents 无向量检索!** 记忆是路径+namespace结构化隔离。语义检索需自己接 pgvector。
  - 更新两路径:热路径(对话中edit_file)+ 后台Cron整合agent(定期提炼合并)。
  - 生产:InMemoryStore(开发)→PostgresStore(生产,store.setup())→LangSmith自动配。并发写冲突:拆文件/追加式/只让后台写共享。
- 自我进化分工:Skill=固化流程(按需激活);AGENTS.md=固化改进指令/风格(启动always加载)。
- pgvector补缺(Phase4):写自定义工具 search_knowledge_base(query) 做embedding+相似度检索给agent;Cron提炼的事实embedding后存pgvector。
- 代码切片:agents/memory_capstone.py —— memory=AGENTS.md + 自更新 + 跨会话持久。
- verify:✅ 机制全验证(AGENTS.md打印显示新准则被正确追加+持久);但模型未遵守风格约束(会话答案不简洁/没加✅)。
- 重要教训:"写进记忆"≠"行为会变"。自我进化生效需 强模型 + verifier强制校验 + 关键准则硬编码。再次印证 Ch1"verifier是瓶颈"。

---

## 🎓 Phase 0 完成!(2026-06-23)8/8 章全部跑通
所有 deepagents 核心机制已学完并各有可运行代码切片:
- Ch1 Harness定位 / Ch2 建agent+工具 / Ch3 虚拟FS+后端+权限 / Ch4 规划+state
- Ch5 子agent+隔离 / Ch6 异步编排(认知,动手并Phase2) / Ch7 Skills / Ch8 长期记忆
代码切片:agents/{first_agent,memory_agent,planning_agent,subagent_demo,skill_agent,memory_capstone}.py + ch07_skills/
全局基础设施:.env多provider + InMemoryRateLimiter限流 + 搜索节流。

## 📍 Phase 1 · MVP 闭环(进行中)
目标(终止条件):建任务 → agent自动完成 → 看板显示结果,端到端跑通。

### 已完成
- 学习产物隔离:agents/ → learning/(含 ch07_skills),产品代码全新建。
- 参考项目:references/fastapi-best-architecture(FBA,已 gitignore)当只读蓝图;Phase3抄RBAC/数据权限(data_scope/data_rule)、Phase5抄审计(opera_log+TraceID)。
- ponytail 已装(防过度设计护栏,full 模式)。
- 策略:极简优先;React+shadcn自建+借鉴FBA后端蓝图;不为通用框架过早抽象。
- **后端骨架(Step1)✅**:backend/app/ {config,database,main} + tasks领域(model/schema/router)。FastAPI+SQLAlchemy+SQLite。三端点 curl 验证通过。
- **接 agent(Step2)✅**:agent_runtime/executor.py(产品自己的干净执行器,不依赖learning/)+ BackgroundTasks。
  状态流转 pending→in_progress→done 验证通过,result 正确写回。
- 技术细节:主键 UUID(stdlib uuid4);后台任务用 FastAPI BackgroundTasks(Celery留后);建表用 create_all(Alembic留后)。均有 # ponytail: 注释标记延后项。
- 服务启动:`uv run uvicorn app.main:app --app-dir backend --port 8000 --reload`

- **前端看板(Step3)✅**:frontend/ = Vite+React+TS+Tailwind v4(手写脚手架,未跑交互向导)。
  src/{api.ts, App.tsx}:三列看板(待办/进行中/完成/失败)+ 新建表单 + 2s 轮询。
  暂未上 shadcn CLI(ponytail:一张表+表单不值得拉 shadcn 机制;Tailwind 基础已就位,以后 shadcn add 即可)。
- **联调验证(Step4)✅ Phase 1 终止条件达成**:playwright 浏览器端到端——表单发任务→后台agent完成→轮询刷新→卡片落"已完成"带结果。
- 启动:后端 `uv run uvicorn app.main:app --app-dir backend --port 8000 --reload`;前端 `cd frontend && pnpm dev`。
- 已知小问题:① Step1 期间(接agent前)建的旧任务卡在 pending,无害;② 浏览器 1 个 console error(疑似 favicon 404,不影响功能,待查)。

## 🎉 Phase 1 · MVP 闭环 完成(2026-06-23)
人发任务 → 后台 deepagents 自动接单完成 → 看板显示结果,浏览器端到端跑通。

## 📍 下一步:Phase 2 · 多 agent 异步编排
目标:任务队列 + 并发 worker(多任务同时跑无串扰)+ 任务拆子任务。对应 Ch6 动手(langgraph dev / 异步)。
也可先做些 Phase1 收尾(UI 美化/shadcn、任务详情、错误重试)。ROADMAP.md 是总蓝图。
