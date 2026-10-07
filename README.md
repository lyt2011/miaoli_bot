# miaoli_bot

一个基于 [Ncatbot](https://github.com/NapNeko/NcatBot) 的 QQ 机器人插件，用 **LangGraph** 自建图管线把 QQ 对话接给 LLM，让 QQ 消息驱动模型思考、回复并调用工具。

- **版本**：0.14.1
- **入口**：`main.py`（插件类 `MiaoLiBot`）
- **运行载体**：Ncatbot 插件系统（NapCat/OneBot 协议）
- **LLM 客户端**：`langchain-openai` 的 `ChatOpenAI`（`base_url` 指向任意 OpenAI 兼容端点）
- **阶段**：插件化拆分完成，当前处于**优化态** —— 主包只剩图管线、checkpointer 适配层与子插件加载框架，业务由子插件提供，后续以补齐错误处理与体验优化为主
- 🔌 **默认跳转**：edgeless 拓扑下「下一个事件是谁」由处理器主动声明，`base_topology` 子插件提供默认顺序（**一个事件一个节点文件**，每个只返回一条 `Goto`），并承担 `ON_AFTER_REQUEST` 的分支判断（末条有 `tool_calls` → 工具循环，否则 → 收尾）。它注册在**最低优先级** `MINIMUM`，任何子插件挂在任何更高档位都能抢在它之前改道或叫停

## 功能特性

- 🧩 **自建图管线（edgeless 拓扑）**：`core.GraphPipeline`（泛型 `GraphPipeline[StateT, ContextT, InputT, OutputT]`，四个 TypeVar 取自 `langgraph.typing`）把「事件 → 处理器」的编排抽成独立类 —— 8 个图事件常量集中在 `consts/graph_events.py`，节点用 `register(event, node, priority=0)` **显式**挂载（同一事件可挂多个，按 `priority` 降序执行，`priority` 大者先跑；档位常量是 `consts/node_priorities.py` 的九档等比阶梯 `MAXIMUM`(9999) … `NORMAL`(0) … `MINIMUM`(-9999)）。`wire()` **不定义任何事件顺序**，只挂 8 个事件节点 + 一条入口边（`START → ON_AGENT_START`）；「下一个事件是谁」由处理器**主动返回跳转指令**决定：`return {...}` 累积增量并继续本事件剩余处理器、`Continue(updates=…)` 停止本事件剩余处理器、`Goto(goto=…, updates=…)` 跳到指定事件、`Abort(reason=…, updates=…)` 中止整轮图。**谁挂在哪个事件上、谁跳向哪里，都由子插件注册时声明**。
- 🔌 **子插件系统**：`core.PluginLoader` 扫描 `sub_plugin.load_from` 下带 `plugin.toml` 的子目录，把每个子目录注册成 Python 包后实例化入口类并调 `on_load()`；子插件通过 `core.Registry` 注册工具 / 解析器 / 图节点；卸载时 `on_close()` 并把整包从 `sys.modules` 抹掉，改完代码重载立即生效。
- 🧠 **LLM 接入**：`main.py` 只把 `provider_name` / `model_name` 两个**名字**写进 state，由 `build_client` 节点（`ON_TURN_START`）读根配置建 `ChatOpenAI` 写进 `runtime.context["client"]`（**刻意不在建实例时绑工具** —— 工具表按身份每请求变化）；`call_llm` 节点用 `runtime.context["tools"]`（来自 `ToolRegistry`）`bind_tools` 后请求模型；工具循环由 `base_topology` 的 `on_after_request` 节点分流 —— 末条消息有 `tool_calls` 就跳 `ON_TOOL_CALLING` 执行工具、再回到 `ON_TURN_START` 重走一轮；没有就跳 `ON_TURN_END` 收尾。
- 🗜️ **上下文压缩**：`context_compactor` 子插件的 `compact` 节点（`ON_BEFORE_REQUEST`，`priority=NORMAL`）读模型真实 `context_window` / `max_tokens` 判阈值（为输出预留空间），超窗时把历史压成一条 `<compaction>` 摘要并用 `Overwrite` 整体替换；保留条数 / 提示词 / 计数方式（`base` 粗估或 `tiktoken` 精确）全部配置化，提示词落在 `data/compact_prompt.md`。
- 📜 **状态与运行时分离**：`models.GraphState`（会话状态：`messages` 用 `add_messages` **进 checkpoint**；`event` / `segments` / `provider_name` / `model_name` / `final_answer` / `system_prompt` 六键用 `Annotated[T, UntrackedValue]` —— 单次 `ainvoke` 内可见、**不落盘**）与 `models.GraphRuntimeContext`（不进 checkpoint 的运行时依赖：`client` / `tools`）分离 —— `context` 不做浅拷贝、结果保持原引用，所以 LLM 客户端 / 锁这类不可序列化对象只能放 `context`（放 state 会因 msgpack 无法序列化而当场崩）。
- 🎛️ **配置模型化（分层 + 更名）**：`PluginConfig` 含 `providers`（`{供应商名: Provider(base_url / api_key / models: {模型名: LLM(protocol / context_window / max_tokens / support_visions)})}` —— 名字由字典键承担）、`account`（`bot_id` / `admin_id` / `bot_nickname` / `admin_nickname`，四项全必填）、`output`、`checkpointer`、`sub_plugin` 与 `session_dir` / `prompt_file` / `system_prompt`；`DirectoryPath` / `FilePath` 让路径在**加载期**就被校验，缺失即 `ValidationError`。
- 🛠️ **工具调用闭环**：工具统一经 `ToolRegistry` 注册、由 `ToolNode` 执行，返回值经 `utils.tool_result_builder` 的 `success` / `fail` / `custom` 收敛成 `{"status": bool, "message": …}`；主包不再内置任何工具，平台 / 系统 / meme / 联网搜索工具全部由内置子插件注册；`tool_permission_manager` 子插件可在此基础上按身份做工具级权限控制（`on_before_request` 摘 `runtime.context["tools"]`，未声明即拒绝）。
- 🔍 **联网搜索**：`web_search` 子插件的 `lang_search` 工具调 langsearch.com 的 `POST /v1/web-search`（**设计上支持多后端**，`config.yaml` 的 `provider` 决定注册哪个工具，目前只适配了 `langsearch`）。**API key 只从环境变量读**（`env_key`，默认 `SEARCH_API_KEY`），不落进随仓库提交的 `config.yaml`。实测**英文检索质量明显优于中文**（技术 / 包名类相关率约 65% vs 30%），工具 docstring 已要求模型优先用英文搜。
- 🖼️ **工具附件兜底**：部分模型不接受 `tool` 消息携带多模态块（无论块里是什么内容都会 `400` 或静默忽略），`tool_attachment_fixer` 子插件的 `fix_tool_attachment` 节点（`ON_TOOL_CALLING`，`priority=NORMAL-2`）把**非字符串**的 `ToolMessage.content` 整体挪进紧跟其后的一条 `HumanMessage`、原 `ToolMessage` 正文换成 `replace_text`；只对 `models` 里声明的模型生效，无改动时返回 `None` 不写增量。
- 🧩 **两级解析链**：`EventParseChain`（群 / 私聊事件元数据）与 `SegmentParseChain`（文本 / AT / 图片 / 文件 / 引用消息段）双链分发，`utils.easier_parser.parse_message` 一步合并产出 `ParseResult(event, segments)` 喂给图；解析器由 `base_parsers` 子插件注册。
- 🖼️ **多类型消息段**：`Text` → `{text}`、`At` → `{at}`、`Image` → `{image, size, is_meme}`（`QQImageSegmentParser` 只接受 QQ 平台侧 `ncatbot.types.qq.QQImage`，`is_meme` 即其 `sub_type` 非 0）、`File` → `{file, size}`、`Reply` → `{reply}`。
- 🦆 **鸭子类型适配**：`adapters/EventAdapter` 不依赖具体 ncatbot 类型，通过属性探测兼容不同消息事件形态（`user_id` / `group_id` / `is_group` / `send`）；`utils.get_id_from_event` 群取 `group_id`、私聊取 `user_id`。
- 🔧 **协议先行**：`protocols/abc/` 定义编译期抽象（`PluginProtocol` / `ChainProtocol` / `StoreProtocol` / `BaseCheckpointerSaverAdapter`），`protocols/runtime/` 定义运行时检查协议（`Parser`，带 `@runtime_checkable`，可 `isinstance` 判定）。
- 🗄️ **checkpointer 适配层**：`checkpointer.database` 在 `memory` / `sqlite` / `postgresql` 之间切换 checkpoint 存储 —— `adapters/check_pointers/` 的三个适配器把 `InMemorySaver` / `AsyncSqliteSaver` / `AsyncPostgresSaver` 收拢成同一门面（`protocols.BaseCheckpointerSaverAdapter`：1:1 转发 `BaseCheckpointSaver` 的同步 / 异步协议方法，`connect(connect_to, **extra)` 建连、`close()` 释放），`main.py` 的 `CPA_MAPPING` 按 `database` 取类，`on_load` 注入图、`on_close` 统一关闭。
- 💾 **共享存储**：`stores/SHARE_STORE` 全局共享容器，键集中定义于 `consts/share_store_keys.py`（`EVENT_PARSER` / `SEGMENT_PARSER` / `TOOL_REGISTRY` / `NCATBOT_API` / `PLUGIN_CONFIG` / `RAW_CONFIG` / `PLUGIN_DIR` / `WORKSPACE_DIR` / `GRAPH_PIPELINE`）。
- 🔔 **事件优先级让位**：`on_message` 以 `priority=-100` 注册，排在后处理的位置 —— 扩展插件可用更高优先级抢先接收并停止事件传播（如 `miaoli_like` 的 `赞我` 用 `priority=100`），被上游截下的消息不会再进入 LLM。
- 🎭 **角色扮演**：内置猫娘「喵璃」人设提示词（`data/prompts/prompt_v1.3.md`，另有 v1.0 ~ v1.2 历史版本）；`account_injector` 子插件的 `inject_account` 节点把人设与管理员 / 机器人的 QQ 号、昵称拼成提示词块，一起写进系统提示词。
- ⏱️ **输出切块与打字延迟**：`utils.split_string` 按 `output.split_separator` 把回复切块（**恒返回列表**：分隔符为 `null` / 空串时整条一块，避免退化成逐字符迭代），跳过空块，每块按 `len(块) * typing_speed ± typing_speed_offset` 随机 sleep 后再发送，模拟真人在打字。
- 🧪 **本地测试（待重写）**：`tests/` 目录（gitignore，不随仓库提交）里的用例针对的是 pi 桥接层，随 0.8.0 重构整体失效。

## 架构设计

```
QQ / NapCat (OneBot)
        │ ncatbot 事件
        ▼
main.py  MiaoLiBot(NcatBotPlugin)      ← config.yaml → models.PluginConfig（providers / account / sub_plugin / …）
        │   ① parse_message（easier_parser 合并 event + segment 两级解析）
        │   ② EventAdapter.build(event) + concatenate_id → session_id（thread_id）
        ▼
chains/  EventParseChain → Group / PrivateMessageEventParser
         SegmentParseChain → Text / At / Image / File / ReplySegmentParser
        │   → ParseResult(event, segments)      （解析器由 base_parsers 子插件注册）
        ▼
core/GraphPipeline.ainvoke({"event", "segments"}, thread_id=session_id, context=…)
        │
        │  START
        ▼
   ON_AGENT_START ── format_input（event + segments → HumanMessage，追加进 messages）
        │            inject_account（账号信息块 + 人设 → system_prompt 键）
        ▼
   ON_TURN_START ── build_client（按 state 的 provider / model 名建 ChatOpenAI → context["client"]）
        ▼
   ON_BEFORE_REQUEST ── pick_tools（按身份裁 tools）→ compact（超窗压缩）
        ▼
   ON_REQUEST ── call_llm ──▶ bind_tools(tools) → ChatOpenAI
        │                                              │
        │                                              ▼
   ON_AFTER_REQUEST ── base_topology: on_after_request（末条有 tool_calls？）
        │
        ├─ 有 tool_calls ──▶ ON_TOOL_CALLING ── invoke_tools（ToolNode → ToolMessage）
        │                                      └── 回到 ON_TURN_START（重走一轮）
        │
        └─ 无 tool_calls ──▶ ON_TURN_END ──▶ ON_AGENT_END ── latest_to_answer（messages[-1] → final_answer）
                                                                ▼
                                                               END

        │  output["final_answer"]（按 output.split_separator 切块 + 打字延迟）
        ▼
adapters/EventAdapter.send(api, …)  ──▶  QQ
```

### 目录结构

```
miaoli_bot/
├── main.py                        # 插件入口：MiaoLiBot（建容器 + 建图 + 起子插件加载器）
├── manifest.toml                  # 插件清单（name / version / entry_class / pip_dependencies）
├── config.example.yaml            # 配置模板（config.yaml 已 gitignore，内含密钥不提交）
├── __init__.py                    # 顶层重导出（consts / GraphState / SHARE_STORE / 构造器 / 协议）
├── adapters/                      # 适配器
│   ├── base_adapter.py            #   BaseAdapter 基类
│   ├── event_adapter.py           #   EventAdapter（user_id / group_id / is_group / send）
│   └── check_pointers/            #   checkpointer 适配器：InMemory / SQLite / Postgresql
├── chains/                        # 责任链实现
│   ├── base_chain.py              #   BaseParserChain：注册 + 分发给首个接受的 parser（短路）
│   ├── event_parse_chain.py       #   EventParseChain
│   └── segment_parse_chain.py     #   SegmentParseChain
├── consts/                        # 常量集中定义
│   ├── graph_events.py            #   8 个图事件名（ON_AGENT_START / ON_TURN_START / …）
│   ├── node_priorities.py         #   九档优先级阶梯（MAXIMUM 9999 … NORMAL 0 … MINIMUM -9999）
│   ├── id_prefix.py               #   会话键前缀（group- / private-）
│   └── share_store_keys.py        #   SHARE_STORE 键名（含 TOOL_REGISTRY）
├── core/                          # 图管线与子插件加载
│   ├── graph/                     #   图管线
│   │   ├── graph_pipeline.py      #     GraphPipeline：register / wire（edgeless）/ compile / ainvoke / _dispatch，与模块级 merge_data / accumulate_data
│   │   └── actions/               #     BaseAction + Continue / Goto / Abort（处理器主动返回的跳转指令）
│   ├── plugin_loader.py           #   PluginLoader：扫 plugin.toml → 注册成包 → 加载 / 卸载子插件
│   ├── registry.py                #   Registry：子插件的注册门面（工具 / 解析器 / 图节点），含全局单例 registry
│   └── tool_registry.py           #   ToolRegistry：按名字存工具（register / remove / tools）
├── data/prompts/                  # 提示词资产（prompt_v1.0.md ~ prompt_v1.3.md）
├── errors/                        # 异常定义
│   ├── base_bot_error.py          #   BaseBotError 基类
│   ├── agent_aborted.py           #   AgentAborted（继承 GraphBubbleUp，从节点中止本轮图运行）
│   ├── pipeline_stop_dispatch.py  #   PipelineStopDispatch（已无消费方，待清理）
│   └── session_manager_closing_error.py # SessionManagerClosingError
├── models/                        # 数据模型
│   ├── config/                    #   PluginConfig / Provider / LLM / Account / OutputConfig / SubPluginConfig / CheckPointerConfig
│   ├── graph_state.py             #   GraphState（进 checkpoint 的只有 messages；其余 6 键用 UntrackedValue 不落盘）
│   ├── graph_runtime_context.py   #   GraphRuntimeContext（不进 checkpoint：client / tools）
│   └── runtime/                   #   Handler（图处理器登记单元）/ ParseResult / DispatchResult
├── plugins/                       # 内置子插件（随仓库提交，加载目录由 sub_plugin.load_from 指定）
│   ├── account_injector/          #   账号注入节点（nodes/ + plugin.toml）
│   ├── base_nodes/                #   图节点（nodes/ + plugin.toml）
│   ├── base_parsers/              #   两级解析器（event_parsers/ + segment_parsers/）
│   ├── base_platform_tools/       #   平台工具（tools/）
│   ├── base_system_tools/         #   系统工具（tools/ + models/ + consts/ + config.yaml 默认值 + README）
│   ├── base_topology/             #   默认跳转（nodes/ 一个事件一个文件 + config.yaml 默认值）
│   ├── context_compactor/         #   上下文压缩（nodes/ + utils/ + models/ + consts/ + data/ 提示词 + config.yaml 默认值 + README）
│   ├── meme_extension/            #   meme 工具（tools/ + core/ + models/ + consts/ + config.yaml 默认值 + README）
│   ├── orphan_tool_fixer/         #   孤儿工具返回修复（nodes/ + utils/ + config.yaml 默认值）
│   ├── pending_tool_fixer/        #   悬空工具调用修复（nodes/ + utils/ + models/ + consts/ + config.yaml 默认值）
│   ├── tool_attachment_fixer/     #   工具附件修复（nodes/ + utils/ + models/ + consts/ + config.yaml 默认值 + README）
│   ├── tool_permission_manager/   #   工具权限控制（nodes/ + models/ + consts/ + config.yaml 权限表 + README）
│   └── web_search/                #   联网搜索（tools/ + models/ + consts/ + config.yaml 默认值 + README）
├── protocols/                     # 抽象协议
│   ├── abc/                       #   编译期抽象：PluginProtocol / ChainProtocol / StoreProtocol / BaseCheckpointerSaverAdapter
│   └── runtime/                   #   运行时检查：Parser（@runtime_checkable）
├── stores/                        # 全局共享存储（SHARE_STORE）
├── tests/                         # 本地 pytest 用例（gitignore，不提交；当前待重写）
└── utils/                         # 工具函数
    ├── easier_parser.py           #   parse_event / parse_segment / parse_message 快捷入口
    ├── easier_sender.py           #   private / group 便捷发送封装
    ├── event_ops.py               #   get_id_from_event（群 → group_id，私聊 → user_id）
    ├── sugar.py                   #   concatenate_id（会话键加 group- / private- 前缀）/ split_string（回复切块，恒返回 list）/ get_thread_id（图内取 thread_id，图外兜底）/ get_tool_calls
    └── tool_result_builder.py     #   custom / success / fail（工具返回值统一契约）
```

## 数据流

1. QQ 消息经 NapCat → ncatbot → 按注册优先级分发给各插件：本插件以 `priority=-100` 排在后处理位置，上游插件若停下事件传播（如 `miaoli_like` 的 `赞我` 用 `priority=100`）本插件就收不到；群聊消息还必须 @ 到 `plugin_cfg.account.bot_id`。
2. `on_message` 先建 `EventAdapter` 与 `session_id`，再调 `parse_message(event, message)`（内部走 `EventParseChain` / `SegmentParseChain`，解析器由 `base_parsers` 子插件注册）→ `ParseResult(event, segments)`。
3. `session_id = concatenate_id(target_id, is_group=is_group)`（群 → `group-<group_id>`，私聊 → `private-<user_id>`），作为 LangGraph 的 `thread_id` —— 同一会话共享同一个 checkpointer（由 `checkpointer.database` 选中的 memory / sqlite / postgresql 实现）里的 checkpoint，跨轮记忆不串台。
4. `graph_pipeline.ainvoke({"event": …, "segments": …, "provider_name": …, "model_name": …}, thread_id=session_id, context={"client": None, "tools": tool_registry.tools})`。
5. `ON_AGENT_START` 的 `format_input` 把 `event` + `segments` 序列化成 JSON 文本包成 `HumanMessage` **追加**进 `messages`；同事件的 `inject_account`（`account_injector` 子插件）把账号信息块 + 人设写进 `system_prompt` 键（**`UntrackedValue` 通道：单次 `ainvoke` 内可见、不写入 checkpoint**）；`ON_TURN_START` 的 `build_client` 按 state 里的 `provider_name` / `model_name` 从根配置建 `ChatOpenAI` 写进 `runtime.context["client"]`。
6. 同一批次里（`ON_BEFORE_REQUEST`，按 priority 降序）：`pick_tools`（`priority=1`）按 `config.yaml` 权限表与 `event.sender.user_id` 摘掉无权使用的工具（未声明的工具默认拒绝并打 warning）、`compact`（`priority=0`，`context_compactor` 子插件）读模型真实 `context_window` / `max_tokens` 判阈值，超窗时把历史压成一条 `<compaction>` 摘要并返回 `{"messages": Overwrite([摘要, *保留窗口])}` 整体替换历史（`Overwrite` 是 langgraph 官方的「绕过 reducer 直接写入」包装，`accumulate_data` 折叠多个处理器的产出时保留它、`merge_data` 构建视图时消费它，因此「整体替换」与其它处理器的「追加 / 定向删除」可以任意顺序组合）；随后 `ON_REQUEST` 先跑 `pending_tool_fixer`（`priority=2`）给悬空的 `tool_calls` 补上合成返回、`orphan_tool_fixer`（`priority=2`）删掉找不到发起者的 `ToolMessage`（两者只在上一轮异常中断留下坏形状时才有产出，历史本就合法时直接返回 `None`、不写任何增量），再由 `call_llm` 以 `[SystemMessage(state["system_prompt"]), *state["messages"]]` 请求模型，返回的 `AIMessage` 追加进 `messages`。
7. `ON_AFTER_REQUEST` 由 `base_topology` 的 `on_after_request` 节点分流（它注册在最低优先级 `MINIMUM`，因此任何插件都能抢在它之前改道）：末条消息带 `tool_calls` → 跳 `ON_TOOL_CALLING`，由 `invoke_tools` 用 `ToolNode` 执行工具、`ToolMessage` 追加进 `messages`，若工具结果是**非字符串**内容（多模态块列表），由 `tool_attachment_fixer` 子插件把它整体挪成一条 `HumanMessage`（原 `ToolMessage` 正文换成 `replace_text`，只对 `models` 里声明的模型生效），然后跳回 `ON_TURN_START` 重走一轮（重跑 `build_client` / `pick_tools` / `call_llm`）；无 `tool_calls` → 跳 `ON_TURN_END`，再经 `on_turn_end` 跳 `ON_AGENT_END`，最后 `on_agent_end` 返回 `Goto(END)` 收尾（`END` 被 langgraph 过滤，于是没有下一跳）。
8. `ON_AGENT_END` 的 `latest_to_answer` 取 `messages[-1]`，是 `AIMessage` 就把 `content` 写进 `final_answer`（否则回退成携带 `thread_id` 的提示文案）。
9. `on_message` 拿 `output` 的 `final_answer`（用 `.get()` 兜底 —— 该键是 `UntrackedValue`，本轮没走到 `on_agent_end` 时不存在）交给 `utils.split_string`，按 `output.split_separator` 切块（**未设置分隔符 → 整条一块**）并跳过空块，每块按 `len(块) * typing_speed ± typing_speed_offset` 随机 sleep 后交给 `EventAdapter.send(self.api, …)` 发回 QQ。
10. 插件卸载（`on_close`）：先显式 `drop` 掉已知键（含 `TOOL_REGISTRY` / `EVENT_PARSER` / `SEGMENT_PARSER` / `GRAPH_PIPELINE`），再 `plugin_loader.unload_all()` 卸载子插件（逐个 `on_close()` 并从 `sys.modules` 抹掉整包），最后 `await self.cpa.close()` 显式关闭 checkpointer（sqlite 关 `aiosqlite` 连接、postgresql 关连接池、memory 无副作用），残留键只记 warning。

## 内置子插件

主包只保留图管线与加载框架，业务能力由子插件提供。以下十三个内置子插件位于本仓库的 `plugins/` 目录，`plugin.toml` 与子插件自带的 `config.yaml` 默认值都随仓库提交（根目录的 `config.yaml` 仍 gitignore，不进版本控制）：

| 子插件 | 提供 |
|---|---|
| `account_injector` | 账号注入：`inject_account` 在 `on_agent_start` 把管理员 / 机器人的 QQ 号与昵称拼进 `system_prompt` |
| `base_nodes` | 图节点：`format_input` / `build_client` / `call_llm` / `invoke_tools` / `latest_to_answer` |
| `base_parsers` | 两级解析器：群 / 私聊事件 + 文本 / AT / 图片 / 文件 / 引用消息段 |
| `base_platform_tools` | 平台工具：发消息 / 发文件 / 下载文件 / 查消息 ID / 撤回消息 |
| `base_system_tools` | 系统工具：`bash` / `read_file` / `write` / `replace` / `read_image`（自带 `config.yaml` 与 `README.md`） |
| `base_topology` | 默认跳转（edgeless 拓扑的顺序来源）：**一个事件一个节点文件**，8 个节点各返回一条 `Goto`，把旧 `wire()` 的静态边与 `tools_condition` 条件边在插件层复原；`on_after_request` 按 `is_tool_calling(messages)` 分流工具循环与收尾。注册在最低优先级 `MINIMUM`，可被任何子插件抢跑 |
| `context_compactor` | 上下文压缩：`compact` 在 `on_before_request`（`priority=0`）读模型真实 `context_window` / `max_tokens` 判阈值，超窗时把历史压成一条 `<compaction>` 摘要并用 `Overwrite` 整体替换；保留条数 / 提示词 / 计数方式全部配置化（`base` 粗估或 `tiktoken` 精确），自带 `data/compact_prompt.md` 与 `README.md` |
| `meme_extension` | meme 工具：归档 / 发送 / 列举 / 按标签搜索 / 按 hash 删除（自带 `config.yaml`）；自带 `README.md` 说明隐私风险 —— 模型可能把用户发的普通图片误归档为表情包 |
| `orphan_tool_fixer` | 坏历史修复：`fix_orphan_tool_message` 在 `on_before_request`（`priority=2`）删掉找不到发起 `tool_calls` 的 `ToolMessage`（只产出定向删除增量） |
| `pending_tool_fixer` | 坏历史修复：`fix_pending_tool_call` 在 `on_before_request`（`priority=3`）给悬空的 `tool_calls` 补一条「工具未执行」的合成 `ToolMessage`（返回 `Overwrite` 整表替换） |
| `tool_attachment_fixer` | 工具附件修复：`fix_tool_attachment` 在 `on_tool_calling`（`priority=-2`）把非字符串的 `ToolMessage.content` 挪进紧跟其后的一条 `HumanMessage`（原 `ToolMessage` 正文换成 `replace_text`），让不接受 `tool` 消息带多模态块的模型不再 `400`；只对 `models` 里声明的模型生效（留空 = 全部），无改动时返回 `None`。自带 `README.md` |
| `tool_permission_manager` | 工具权限控制：按自带 `config.yaml` 的权限表（`admin` / `white_list` / `anyone`），在 `on_before_request` 把当前身份无权使用的工具从 `runtime.context["tools"]` 摘掉；未声明的工具默认拒绝并打 warning。自带 `README.md` |
| `web_search` | 联网搜索：`lang_search` 调 langsearch.com 的 `POST /v1/web-search`，原始响应整体交给模型。**API key 走环境变量**（`env_key`，默认 `SEARCH_API_KEY`），不写进 `config.yaml`。`provider` 字段留了多后端位置，目前只适配 `langsearch`。自带 `README.md` |

> `orphan_tool_fixer` 与 `pending_tool_fixer` 成对：前者治「有返回没请求」，后者治「有请求没返回」。两者互不依赖、各自独立判断，谁先跑都不影响结果（`accumulate_data` 保证不同形态的增量可以任意顺序折叠）；触发场景是上一轮工具执行中途异常／并发冲突导致消息形状坏掉，此后每轮请求模型都会 `400 insufficient tool messages following tool_calls`。

子插件约定：目录下放 `plugin.toml`（`enter_class` / `enter_file`）与可选 `config.yaml`；入口类继承 `PluginProtocol`，在 `on_load` 里用 `Registry` 注册工具 / 解析器 / 图节点，在 `on_close` 里释放资源。

## 安装与使用

1. 将本目录放入 ncatbot 的插件目录（如 `plugins/miaoli_bot`）。
2. 确认运行环境已安装依赖（`manifest.toml` 的 `pip_dependencies` 会在 `plugin.auto_install_pip_deps` 打开时自动安装）：
   - `ncatbot`（`>=5.5.8`）
   - `langgraph`（`>=1.2.12`）
   - `langchain-core`（`>=1.6.5`）：`@tool` 工具定义 / `BaseMessage` / `BaseChatModel` 等基础类型
   - `langchain-openai`（`>=1.6.6`）
   - `langgraph-checkpoint-sqlite`（`>=3.1.1`，`database: sqlite` 时用到）
   - `langgraph-checkpoint-postgres`（`>=3.1.2`，`database: postgresql` 时用到）
   - `aiosqlite`（`>=0.22.1`）/ `psycopg`（`>=3.3.6`）/ `psycopg-pool`（`>=3.3.3`）：直接 import 的驱动与连接池（`SQLiteAdapter` / `PostgresqlAdapter` / `MemeSqlite`）
   - `aiofiles`（`>=24.1.0`）：`base_system_tools` 的 `write` / `replace` 工具异步写盘
   - `aiohttp`（`>=3.13.4`）：`web_search` 的 HTTP 客户端（`ClientSession`）
   - `pydantic`（`>=2.13.5`）：配置模型（`models/config/`）与各工具的参数 schema
   - `pyyaml`（`>=6.0.3`）：子插件 `config.yaml` 解析（`core/plugin_loader.py` 的 `yaml.safe_load`）
   - `filetype`（`>=1.2.0`）
   - `pillow`（`>=12.3.0`）
   - `tiktoken`（`>=0.14.0`）
3. 插件配置：`cp config.example.yaml config.yaml` 后填真实 `api_key`（`config.yaml` 含密钥、已 gitignore）。插件目录的 `config.yaml` 为默认值，全局 `config.yaml` 的 `plugin.plugin_configs.miaoli_bot` 同键覆盖；`on_load` 第一步即 `PluginConfig.model_validate(self.config)`，必填项缺失 / 路径不存在 / 类型不符都会抛 `ValidationError`，本插件加载失败并在日志留下 traceback（机器人其余部分不受影响）。

配置键名与 `models.PluginConfig` 的字段一一对应：

| 键 | 默认 / 必填 | 用途 |
|---|---|---|
| `providers` | `{}` | 供应商字典，键 = 供应商名，值 `Provider(base_url / api_key / models)` |
| `providers.<供应商名>.base_url` | **必填** | 请求地址（**不会拼路径**，填到 `/v1` 这一层） |
| `providers.<供应商名>.api_key` | **必填** | 鉴权密钥 |
| `providers.<供应商名>.models` | `{}` | 模型字典，键 = 模型名，值 `LLM(protocol / context_window / max_tokens / support_visions)`；`protocol` 必填，`support_visions` 至少一项 |
| `account` | **必填** | `bot_id` / `admin_id` / `bot_nickname` / `admin_nickname`，四项全必填；`account_injector` 子插件的 `inject_account` 用它拼提示词块，`admin_id` 也是工具权限插件判定管理员的依据 |
| `session_dir` | `gettempdir()`（`/tmp`） | 会话保存路径（`DirectoryPath` 校验存在性） |
| `prompt_file` | `null` | 系统提示词文件（`FilePath` 校验存在性，加载时按 UTF-8 读入），优先于 `system_prompt` |
| `system_prompt` | `null` | 内联系统提示词，仅在未配置 `prompt_file` 时使用（可为 `null`） |
| `output` | `OutputConfig()` | `typing_speed`（默认 `0.01`，每个字的打字时间）/ `typing_speed_offset`（默认 `0`，随机延迟偏移）/ `split_separator`（默认 `null`，输出切块分隔符；空串会被校验拒绝，`null` 表示整条不切块）—— `on_message` 用它把回复切块并按字数模拟打字延迟 |
| `checkpointer` | `CheckPointerConfig()` | `database`（`memory` / `sqlite` / `postgresql`，默认 `memory`）/ `connect_to`（数据库地址，**非 `memory` 必填**）/ `extra`（额外参数，透传给适配器的 `connect(**kwargs)`；postgresql 认 `max_size` 默认 8 / `min_size` 默认 4 / `autocommit` 默认 `true` / `row_factory` 默认 `dict_row`）—— `on_load` 按 `database` 从 `CPA_MAPPING` 取适配器并 `connect`（**0.9.0 起已接线**），`on_close` 调 `close()` |
| `sub_plugin` | `SubPluginConfig()` | `is_enable`（默认 `false`，**当前未消费**）/ `load_from`（子插件目录，`Path`）；`PluginLoader` 扫描该目录下带 `plugin.toml` 的子目录并加载 |

4. 启动 bot，在 QQ 中私聊或群聊（群聊需 @ 机器人）即可与模型对话。

### 本地测试

```bash
cd <插件父目录>          # plugins/
<venv>/bin/python -m pytest miaoli_bot/tests/ -v
```

> 注：`tests/` 里的用例仍是针对 pi 桥接层写的，随 0.8.0 重构整体失效，待重写。

## 依赖

| 包 | 用途 |
|---|---|
| `ncatbot`（`>=5.5.8`） | QQ 机器人框架 / 事件与消息 API |
| `langgraph`（`>=1.2.12`） | 图管线（`StateGraph` / `Command` / `Overwrite` / `ToolNode` / checkpoint） |
| `langchain-openai`（`>=1.6.6`） | `ChatOpenAI`（可指向任意 OpenAI 兼容端点） |
| `langchain-core`（`>=1.6.5`） | `@tool` 工具定义、`BaseMessage` / `BaseChatModel` 等基础类型（主包与子插件都用） |
| `langgraph-checkpoint-sqlite`（`>=3.1.1`） | `AsyncSqliteSaver`（`checkpointer.database: sqlite`），带 `aiosqlite` / `sqlite-vec` |
| `langgraph-checkpoint-postgres`（`>=3.1.2`） | `AsyncPostgresSaver`（`checkpointer.database: postgresql`），带 `psycopg` / `psycopg-pool` |
| `aiosqlite`（`>=0.22.1`） | `SQLiteAdapter` 与 `meme_extension.MemeSqlite` 共用的异步 sqlite 驱动（连接分别由 `close()` / `__aexit__` 关） |
| `aiofiles`（`>=24.1.0`） | `base_system_tools` 的 `write` / `replace` 工具异步写盘（`aiofiles.open` + `async with`） |
| `aiohttp`（`>=3.13.4`） | `web_search` 的联网搜索请求（`ClientSession.post`）；它也是 `ncatbot5` 的传递依赖，此处显式声明 |
| `psycopg`（`>=3.3.6`）/ `psycopg-pool`（`>=3.3.3`） | `PostgresqlAdapter` 直接 import 的驱动与连接池（`AsyncConnectionPool`） |
| `pydantic`（`>=2.13.5`） | 配置模型（`BaseModel` / `Field` / `model_validator`）与工具参数 schema |
| `pyyaml`（`>=6.0.3`） | `core/plugin_loader.py` 读子插件 `config.yaml` 的 `yaml.safe_load` |
| `filetype`（`>=1.2.0`） | `base_system_tools` 的图片类型嗅探（`read_image`） |
| `pillow`（`>=12.3.0`） | `context_compactor` 的图片宽高解析（`image_to_tokens`，据此估算图片 token） |
| `tiktoken`（`>=0.14.0`） | `context_compactor` 的精确 token 计数（`calculate.mode: tiktoken`） |

> 注：以上依赖由 `manifest.toml` 的 `pip_dependencies` 声明。
> 注：0.7.0 及以前依赖 `pi_bridge` 与外部 pi Agent 进程，0.8.0 起已整体移除。

## 项目状态

v0.14.1 — **补上 `web_search` 的权限声明，并把服务器部署的密钥配置收口**：`tool_permission_manager/config.yaml` 补 `lang_search` → `anyone`（15 → 16 条，与注册表 16 个工具一一对应）—— 此前它是唯一未声明项，按「未声明即拒绝」会被摘掉并每轮打 warning。**服务器部署 0.13.0 → 0.14.1**：rsync（`--delete` + 排除 `.git` / `__pycache__/` / `*.pyc` / `*.log` / `.ruff_cache/` / **`config.yaml`**）共 10 个文件更新 + 10 个新增、0 删除；`web_search` 与 `tool_permission_manager` 的 `config.yaml` 因被排除而单独 `scp`（md5 与仓库一致），根 `config.yaml` 未被触碰（md5 `11314fd7a0b43857f100974a840ea740` 前后一致）。**API key 写进 systemd unit** —— `/etc/systemd/system/ncatbot.service` 新增 `Environment=SEARCH_API_KEY=…`，`daemon-reload` 后 `systemctl show` 可见，文件权限 `644` → **`600`**（现含密钥），并从 `/proc/<pid>/environ` 确认密钥真进了 bot 进程。**服务器侧独立验证**（Python 3.12）：子插件 **13/13**、工具 **16 个**、权限表 16 条且与注册表零差异、管理员 16 / 路人 10 个工具且 `lang_search` 双方可见、启动日志无 ERROR。**⚠️ 服务器出口网络限制（本次新发现）**：该服务器只能访问国内服务 —— `api.deepseek.com` / `www.bing.com` / `api.bochaai.com` 可达，而 `api.langsearch.com` / `api.tavily.com` / `api.search.brave.com` / `google.serper.dev` / `duckduckgo.com` / `github.com` / `api.openai.com` **全部连接超时**（3/3 重试一致），故 `lang_search` 在服务器上当前不可用，调用返回 `fail("联网搜索出错: TimeoutError: ")` —— 已验证是优雅降级（返回 `fail` 字典、不抛异常、不打断图）。排查中另发现 systemd-resolved 对 `api.langsearch.com` 返回伪造 `cname.lab.`（DNS 污染残留），`resolvectl flush-caches` 后解析恢复，但**根因是出口网络限制而非 DNS**。**未验证**：NcatBot 运行时下的端到端对话仍未跑。

v0.14.0 — **新增 `web_search` 子插件（LangSearch 联网搜索），并把 7 个工具函数签名里的默认值全部去掉**：`lang_search` 把 langsearch.com 的 `POST /v1/web-search` 接给模型（`query` / `count`（默认 `5`，`1~50`）/ `freshness` / `include_domains` / `exclude_domains` / `timeout`），请求体传 `summary: False`、域过滤用 camelCase 名（`includeDomains` / `excludeDomains` —— 服务端只认这个，snake_case 会被**静默忽略**），原始响应经 `success()` 整体交给模型。`aiohttp.ClientSession` 由 `on_load` 建、`on_close` 关；**API key 只从环境变量读**（`env_key`，默认 `SEARCH_API_KEY`），存 `PrivateAttr` 里、只暴露只读属性 `api_key`，**不落进随仓库提交的 `config.yaml`**（本插件是全仓第一个从环境变量取密钥的子插件）。`provider` 字段留了**多后端**位置（`Literal["langsearch"]`），目前只适配 `langsearch`。**7 个工具函数签名去掉默认值（共 12 处，行为零变化）**：`bash` / `read_file` / `write` / `replace` / `send_file_to_qq` / `send_message_to_qq` / `send_meme_to_qq` —— `@tool(args_schema=…)` 下 `ToolNode` 走 `tool.ainvoke`，先用 `args_schema` 校验并填默认值再调函数，实测 schema 默认值**覆盖**函数默认值，故函数侧是纯冗余；删掉后模型看到的 JSON Schema 逐字未变。`manifest.toml` 新增 `aiohttp`（`>=3.13.4`，15 → 16 项）。**修 3 处必崩 + 补导入导出**：`PrivateAttr(..., description=…)` 的 `TypeError`、`os.environ[env_key]` 缺 `self.` 的 `NameError`、`PrivateAttr(...)` 使 `_api_key` 完全不创建导致环境变量缺失时 `AttributeError`；`tools/lang_search.py` 7 处缺导入（17 处 `F821`）、`tools/__init__.py` 补导出、`main.py` 补 `aiohttp` 与两个常量；`lang_search` 的 `response.status_code` → `response.status`、比较值 `288` → `200`（实测服务端返回 `200`）—— 修好后 `try/except` 才真正拦住「4xx/5xx 被 `success()` 包成 `status: true` 交给模型」。**实测**：英文检索质量明显优于中文（技术 / 包名类相关率约 **65% vs 30%**，`What is NcatBot` 命中 PyPI 的 `ncatbot` 系列而中文版 0/5），工具 docstring 已要求优先用英文；`summary: False` 省 **68%**（`count=5`：3252 → 1929 token）；单次平均 **1822 token**，`count=50` 时 **27786 token**；响应信封噪声仅占 **14%**，故不做字段过滤。**验证**：全仓 `compileall` rc=0、`ruff --select F,E9` 仅剩 4 处既有（均不在本次改动文件内）、全量插件加载 **13/13**、工具 **16 个**、`lang_search` 真实 API 端到端 6/6 `status=True`、环境变量缺失不崩（返回空串）、`provider` 非法值 `ValidationError`、桩 session 抓 payload 确认 `summary: false` 与 camelCase 生效、7 个工具的「函数无默认值 + schema `default` 仍在」逐项核对、真实 `ToolNode` 注入值与改动前逐字一致、`manifest.toml` 经 `tomllib` 解析、导入对齐逐文件核对。**未验证**：NcatBot 运行时下的端到端对话仍未跑；服务器侧 `SEARCH_API_KEY` 环境变量尚未配置。

v0.13.0 — **工具附件修复从 `base_nodes` 拆出、独立成子插件 `tool_attachment_fixer`（破坏性）**：`base_nodes/nodes/_attach_image.py` 整个删除（119 行，含 `_pick_images` / `_pick_text` 两个私有辅助与 `DEFAULT_NOTICE` / `IMAGE_PREFIX` 两个常量），其 `on_tool_call(attach_image, priority=NORMAL-1)` 注册与导入导出同步移除。新插件的 `fix_tool_attachment` 节点改挂 `ON_TOOL_CALLING`（`priority=NORMAL-2`），行为上有四处有意差异：① **只对 `models` 里声明的模型生效**（`<provider>/<model>` 与 `<model>` 两种写法都认，留空 = 全部）—— 旧节点对所有模型无条件改写，而实际只有部分模型拒绝 `tool` 消息带多模态块；② **扫描全表**而非只扫末尾连续的一段 `ToolMessage` —— 旧节点依赖「附件只可能出现在本轮最后一条消息」的隐含前提，历史里有旧残留时永远修不到，而那类残留恰恰每轮 `400`；③ **搬运整个 content 列表**而非只挑图片 —— 旧节点的 `_pick_images` 只认 `type in ("image", "image_url")`，其余模态块（`audio` 等）**静默丢弃**（实测确认）；④ **原地改 `content`** 而非新建 `ToolMessage` 逐字段复制。判据 `isinstance(content, list)` 等价于「非字符串」—— `ToolMessage` 会把 `dict` / `None` / `int` 等非 list 输入全部 coerce 成 `str`（实测 `None → 'None'`、`123 → '123'`），所以 `.content` 只可能是 `str` 或 `list` 两种。新建的 `HumanMessage` 带确定性 `id`（`f"image-{tool_call_id}"`，旧节点是 `f"images-{tc1}-{tc2}"` 合并成一条）；无改动时返回 `None` 不写任何增量。判据函数收进 `utils/guards.py`（`is_target_model` / `is_tool_message` / `is_block_content` / `is_target_message`，依赖方向 `nodes → utils → consts`），节点文件只剩主函数。**破坏性**：不加载 `tool_attachment_fixer` 时工具附件不再被改写（旧行为是 `base_nodes` 无条件提供）。**顺带**：修两处陈旧注释（`base_nodes/nodes/call_llm.py` 的「已由 `compact` 写进」→ `context_compactor`；`pending_tool_fixer/main.py` 的「高于 `compact(1)`」删除 —— 该节点已不在同一事件上，`(1)` 还是 0.12.0 前的旧值）。**验证**：全仓 `compileall` rc=0、`ruff --select F,E9` 仅剩 4 处既有（`main.py:153` F841、`bash.py:40/41` F541、`sugar.py:50` F541，均不在本次改动文件内）、全量插件加载 **12/12**、`ON_TOOL_CALLING` 为 `invoke_tools(0) → fix_tool_attachment(-2) → 默认跳转(-9999)`、全仓 `attach_image` 残留 0（README 里两处是历史版本记录）、`base_nodes` 的 `compact` 残留 0、迁移前后主函数 AST 级逐字相同、**新旧节点 5 组用例对照实测**（末尾单条带图 / 只有文本块 / 带图但在中间 / 末尾两条连续 / 混合块含 audio）、命中模型 → `Overwrite`、未命中 → `None`、纯文本输入 → `None`、**第二次跑 → `None`（幂等）**、`utils.__all__` 逐项可解析。**未验证**：NcatBot 运行时下的端到端对话仍未跑；「模型确实对非字符串 `tool` 消息报错」是用户实测结论，仓库内未复现。

v0.12.0 — **上下文压缩从 `base_nodes` 拆出、独立成子插件 `context_compactor`；`GraphState` 的 6 个非持久化键改用 `UntrackedValue`（破坏性）**：`base_nodes/nodes/_compact.py` 整个删除 —— 它把 `CONTEXT_WINDOW = 128000` 写死在代码里（原注释即标 `# HACK`）、token 用「字符数求和」粗估、提示词与保留条数都是模块级常量。新子插件的 `compact` 节点改挂 `ON_BEFORE_REQUEST`（`priority=NORMAL`），流程为「算 token → 比阈值 → 压 → 整体替换」：阈值判断 `usage_tokens + max_tokens < context_window` 时不压、直接返回 `None`（不写任何增量，为输出预留空间）；压缩请求体为 `[SystemMessage(system_prompt), *messages, HumanMessage(prompt)]`（无 `system_prompt` 时省略）；返回 `{"messages": Overwrite([HumanMessage("<compaction>摘要</compaction>"), *最近 keep_count 条])}`。保留规则从后往前收，只对 `HumanMessage` / `AIMessage` / `SystemMessage` 计数，**`ToolMessage` 不占配额**（避免把「有请求没返回」的 `tool_calls` 切开）。**全部配置化**：`keep_count` / `encoding` / `prompt_file`（绝对路径）/ `calculate.mode`（`base` 粗估或 `tiktoken` 精确）/ `calculate.encoder`（`o200k_base` / `cl100k_base`，`mode=tiktoken` 时必填，由 `CalculateConfig` 的 `model_validator` 校验）；提示词落在 `data/compact_prompt.md`，懒加载。utils 拆成四个单向依赖模块 `easier_calculate → sugar → block_ops → image_ops`。**图片 token 估算**：`image_to_tokens` 用 `int(sqrt(min(宽,1920) × min(高,1080)))` 折算，占位符取汉字 `图`（在 `o200k_base` 里**严格 1 字符 = 1 token**；可打印 ASCII 全部会被 BPE 合并，实测 `'a'×1000 → 125 token`；`\0` 也会 2 字符并成 1 token）。**`GraphState` 改造**：`event` / `segments` / `provider_name` / `model_name` / `final_answer` / `system_prompt` 六键由普通键改为 `Annotated[T, UntrackedValue]` —— 只在单次 `ainvoke` 内可见、不写入 checkpoint（实测 `channel_values` 从 7 个键降到**只剩 `['messages']`**，20 轮真实对话**省 34%** 存储）；`main.py` 的取值相应改 `.get()` 兜底 + warning（`ainvoke` 在无任何通道值时返回 `None`，原下标写法会 `KeyError`），并顺带修掉「不写的轮次带回上一轮旧值」的陈旧读。**破坏性**：① `base_nodes` 不再提供上下文压缩，升级后需自行加载 `context_compactor`；② 上述 6 键不再跨轮持久化；③ `manifest.toml` 新增 `pillow` / `tiktoken`。**修掉 9 处必崩**：`context_compactor` 的 `PrivateAttr(description=...)` `TypeError`、`Field(default=CalculateConfig)` 实例共享、`encoding.encode(contents)` 里 `contents` 未定义 `NameError`、入口类没继承 `PluginProtocol`、`enable` 判断逻辑反了、`state["provider"]` 键名错、`utils/sugar.py` 的 `except <???>:` `SyntaxError`、`image.weight` 拼写错、`data:` 前缀未剥掉（缺赋值）；另补 6 个文件 8 处缺导入（服务器 Python 3.12 注解立即求值，漏导入会直接 `NameError`）。**顺带**：`base_calculate` 公式由 `len(contents)` 改为 `int(len(contents) * 0.7)`（原式相当于 1 token/字，实测真实语料约 0.55 tok/字、纯中文约 0.9，触发点被推到 96% 以上；新系数触发时占用约 76%）、`prompt` 属性返回类型由 `str` 修正为 `Optional[str]`、`node_connection_fix` → `base_topology` 改名落地（0.11.0 提交信息里写的是旧名）、两个 fixer 的注册事件从 `on_before_request` 移到 `on_request`、补齐 7 份子插件 README（11/11 全覆盖）。**验证**：全仓 `compileall` rc=0、`ruff --select F401,F811,F821,F841` 只剩 `main.py:153` 一处既有 F841、全量插件加载 **11/11**（`ON_BEFORE_REQUEST: pick_tools(1) → compact(0) → 默认跳转(-9999)`）、`compact` 实跑（低于阈值 `None` / 超阈值 `Overwrite` 6 条）、`image_to_tokens` 真 PNG 全链路与 7 组边界、`on_close` 的 `drop` 生效、**服务器 Python 3.12** 独立验证、`manifest.toml` 经 `tomllib` 解析。**未验证**：NcatBot 运行时下的端到端对话仍未跑；`tiktoken` 模式未在服务器验证（连不上 `openaipublic.blob.core.windows.net`，编码文件下不下来，故默认 `mode: base`）。

v0.11.0 — **补上 0.10.0 留下的缺口：新增 `base_topology` 子插件，图重新可端到端跑通（破坏性）**：0.10.0 把 `wire()` 改成 edgeless 之后，`tools_condition` 条件边随之一并删除，「下一个事件是谁」改由处理器主动返回跳转指令决定，但当时**没有任何处理器负责这件事** —— 图跑完 `ON_REQUEST` 就静默结束、`final_answer` 缺失、`main.py` 当场 `KeyError`。本版补上的 `base_topology` 就是那个「默认跳转」：**一个事件一个节点文件**（`nodes/on_agent_start.py` / `on_turn_start.py` / … / `on_agent_end.py`），每个节点只返回一条 `Goto`，把旧 `wire()` 的 8 条静态边与那条条件边**原样搬到插件层**（`ON_AFTER_REQUEST` 该去 `ON_TOOL_CALLING` 还是 `ON_TURN_END` 的分支判断由节点里的 `is_tool_calling(messages)` 承担）。它注册在**最低优先级** `MINIMUM`，因此任何子插件挂在任何更高档位都能抢在默认跳转之前改道或叫停。**破坏性变更**：优先级常量从 `EARLIEST`(200) / `LATEST`(-200) / `NORMAL`(0) **三档改为九档等比阶梯** —— `MAXIMUM`(9999) / `HIGHEST`(1000) / `HIGH`(100) / `MEDIUM`(10) / `NORMAL`(0) / `LOW`(-10) / `LOWEST`(-100) / `TRIVIAL`(-1000) / `MINIMUM`(-9999)，`EARLIEST` 与 `LATEST` **两个名字已不存在**；改等比阶梯的理由是插件里已经在用 `NORMAL+1` / `NORMAL+2` / `NORMAL+3` 这类微调，档间差 10 倍才能保证这些微调不跨档（如 `MEDIUM+3`=13 仍 < `HIGH`=100）。**一处有意为之的拓扑差异**：旧静态边是 `ON_TOOL_CALLING → ON_BEFORE_REQUEST`，新默认跳转改成回 `ON_TURN_START`，即每轮工具调用都重走一遍「轮开始」（会重建一次 `Chat[OI]`，幂等），这是刻意模仿 pi 的回合语义。**修掉 2 个必崩项**：① `consts/node_priorities.py` 六个名字写成了空值（`HIGHEST\t= ` 没有右值），`import miaoli_bot.consts` 直接 `SyntaxError`；② `consts/__init__.py` 的导出表仍是 `from .node_priorities import EARLIEST, LATEST, NORMAL`（这两个名字在新文件里已不存在）→ `ImportError`。另修 `base_topology` 自身：`on_after_request.py` 的 `messages: ???` 与 `on_turn_end.py` 缺函数名两处 `SyntaxError`、8 个节点文件全缺 `Goto` / `ON_*` / `END` 导入、`is_tool_calling` 在空列表时返回 `[]` 而非 `bool`、`nodes/__init__.py` 导出为空。**验证**：`compileall` 全仓 rc=0、`ruff --select F401,F811,F841` 仅剩 `main.py:158` 一处既有 F841、`consts.__all__` 28 项**逐项可解析**、九档值 `9999 1000 100 10 0 -10 -100 -1000 -9999`（严格递减 + 上下对称）、全量插件加载 **10/10**、8 个事件处理器列表**末位均为默认跳转且 `priority=-9999`**、**端到端正常路径**（真插件 + 真 config + 假模型）`final_answer='（假模型回复）'`、**端到端工具路径** 模型调用 **2** 次且消息序列 `[HumanMessage, AIMessage, ToolMessage, AIMessage]`、`final_answer='结果是 3'`、**覆盖能力** 在 `ON_AGENT_START` 挂一个 `NORMAL` 优先级的「抢跑」处理器返回 `Goto(ON_AGENT_END)` 时轨迹为 `['inject_account', 'format_input', 'hijack']`（默认跳转被短路、未执行）、回归套件 `accumulate_unit_test` **27/27** + `fixer_test2` **31/31** + `candidate_g_test` **18/18** + `compact_dispatch_check` **7/7**。**未验证**：NcatBot 运行时下的端到端对话（`on_message` → 发送循环）仍未跑；本版**只在真实插件 + 真实 config + 假模型下验证**，未真实调用 LLM 端点。

v0.10.0 — **`GraphPipeline` 重构：拓扑从「静态边」改为「事件节点 + 主动跳转」，控制流从异常改为返回值（破坏性）**：`wire()` 不再定义任何事件顺序，只挂 8 个事件节点 + 一条入口边（`START → ON_AGENT_START`）；「下一个事件是谁」改由处理器**主动返回跳转指令**决定。为此新增 `core/graph/actions/` —— 空基类 `BaseAction` 与 `Continue`（停止本事件剩余处理器，替代旧 `PipelineStopDispatch` 的 `break`）/ `Goto`（跳到指定事件，携带 `updates`）/ `Abort`（中止整轮图，转成 `AgentAborted` 抛出）三个 Action。**「纯增量」的表达统一成裸 `dict`** —— 原来的 `Update` 包装类整个删除（它的存在与「能带增量」无关：后者是属性不是类型），现有 6 个返回裸 dict 的节点**零改动**即可用。**命名收口**：事件名去掉 `miaoli_bot/` 前缀（`miaoli_bot/graph.event.on_agent_start` → `__on_agent_start__`）；`MAX_PRIORITY` / `MIN_PRIORITY` / `DEFAULT_PRIORITY` → `EARLIEST` / `LATEST` / `NORMAL`（4 个子插件共 11 处引用同步）；`core/graph_pipeline.py` → `core/graph/graph_pipeline.py`；`consts/graph.py` 拆成 `graph_events.py` + `node_priorities.py`；`_merge` / `_accumulate` 搬出类成模块级纯函数并更名 `merge_data` / `accumulate_data`。**关键设计点**：`is_update_action` 必须同时认「裸 dict」与「Action 自带的 `updates`」—— 只认前者会让 `Goto` / `Continue` / `Abort` 携带的增量被静默丢弃（实测 `Overwrite` 丢失后 `messages` 不再被替换），只认后者会让现有插件全部失效。**⚠️ 图当前无法端到端跑通**：`tools_condition` 条件边随 `wire()` 删除，替代它的默认跳转插件尚未实现，图跑完 `ON_REQUEST` 即静默结束（`final_answer` 缺失 → `main.py` `KeyError`）。**验证**：`compileall` 全仓 rc=0、`ruff --select F401,F811,F841` 仅剩 `main.py:158` 一处既有 F841、全量插件加载 **9/9** 与 15 个工具、四个 Action 逐形态真跑（裸 dict / `None` / `Continue` 带与不带 updates / `Goto` 带与不带 updates / `Abort` / 未知对象兜底）、**端到端 Goto 链** `RUN=['start','turn','end']` 且 `final_answer='答完了'`（`Overwrite` 经 `Goto(updates=…)` 正确生效）。**未验证**：NcatBot 运行时下的端到端对话未跑；`orphan_tool_fixer` / `pending_tool_fixer` 的优先级关系在新常量名下未重跑 `fixer_test2`。

v0.9.12 — **修复 `GraphPipeline` 增量归约不满足结合律的 bug，并新增两个坏历史修复子插件**：`_dispatch` 此前把同一事件里各 handler 的返回值用 `_merge` 两两折叠，而 `_merge` 走 `add_messages` —— 它**只在新来的那一份里找 `REMOVE_ALL_MESSAGES` 标记**（`langgraph/graph/message.py`：`if remove_all_idx is not None: return right[remove_all_idx + 1:]`），于是后一次「整表重写」会把前面积累的删除指令**静默丢弃**。后果是 `compact` 与 `call_llm` 的优先级一旦反序，压缩就被整个吞掉（实测 30 → 32 条，消息数不降反升）；这是已发布代码里潜伏的 bug（0.9.11 及之前都有）。修法：新增 `_accumulate` 专管「增量∘增量」折叠，让替换包装活到框架真正应用增量的那一刻；`_merge` 一行未动，继续只负责「增量 → 视图」。同时把「整表重写」的表达从 langchain 内部哨兵 `RemoveMessage(id=REMOVE_ALL_MESSAGES)` 换成 langgraph 官方 `Overwrite`（`from langgraph.types import Overwrite`），插件侧不再手搓内部哨兵、框架也不再解析它（`_has_reset` / `_strip_reset` 两个辅助函数随之删除）。**新增两个子插件**：`pending_tool_fixer`（`priority=3`）给悬空的 `tool_calls` 补一条合成 `ToolMessage`（`status="error"`、`id=f"auto-fix: {tool_call_id}"`），`orphan_tool_fixer`（`priority=2`）删掉找不到发起者的 `ToolMessage`（只产出定向删除增量）；两者互不依赖，专治上一轮工具执行中途异常留下的坏形状（此后每轮请求模型都会 `400 insufficient tool messages following tool_calls`）。**同时收口改名与校验**：子插件目录 `account_inject/` → `account_injector/`（README / `config.example.yaml` 同步）；`LLM.visions` → `LLM.support_visions`、`Vision` 字面量去掉 `tool_calls`；`providers` / `Provider.models` 加 `min_length=1`（空配置直接在校验期拒绝）；`latest_to_answer` 在末条非 `AIMessage` 时改为提示携带 `thread_id` 反馈。**验证**：`fixer_test2` **31/31**（含真实坏数据 550 → 551、优先级正/反序、幂等、边界）、`accumulate_unit_test` **27/27**、`candidate_g_test` **18/18**、`compact_dispatch_check` **7/7**（反序 30 → 6）、`overwrite_graph_e2e_test` **15/15**（真实编译图 + checkpointer，含通道 MISSING 时首写 `Overwrite`）、全量插件加载 **9/9**、端到端 `ainvoke` 管理员 15 工具 / 路人 9 工具。**未验证**：NcatBot 运行时下的端到端对话未跑；`_compact.py` 的 `CONTEXT_WINDOW` 仍是硬编码 `128000`。

v0.9.11 — **LLM 实例改为图内按需创建，并补齐这轮重构留下的坑**：`ChatOpenAI` 不再在 `main.py` 里硬编码（`model="deepseek-flash"` + `providers[0]`），改为 `main.py` 只把 `provider_name` / `model_name` 两个名字写进 state，由新节点 `build_client`（`ON_TURN_START`）读根配置建实例写进 `runtime.context["client"]`（**刻意不绑工具** —— 工具表按身份每请求变化，绑定留在 `call_llm`）；`runtime.context` 的 `chat_model` 更名 `client`，并移除 `plugin_config`（配置统一走 `SHARE_STORE`）。`format_prompt` 从 `base_nodes` 拆出，独立成子插件 `account_inject`（`ON_AGENT_START`，入口类 `AccountInjector`）。`providers` / `models` 由 list 改为 dict（`name` 字段交给字典键承担），`LLM.protocol` 变必填、`visions` 加 `min_length=1`，`consts/graph.py` 新增 `DEFAULT_PRIORITY`。**修掉 4 个必崩项**：`main.py` 的 `providers.keys()[0]`（`dict_keys` 不可下标）与未定义的 `provider`、`build_client` 缺 `SHARE_STORE` / `PLUGIN_CONFIG` 导入、`plugin.py` 缺 `Dict` 导入、`base_nodes/main.py` 残留的 `inject_account` 导入；`config.example.yaml` 同步迁移到 dict 结构（照抄旧模板会 `ValidationError`）；删掉 3 处多余导入（`InMemorySaver` / `List` / `Registry`）。**验证**：`compileall` 全仓 rc=0、`ruff --select F401` 全仓 `All checks passed!`；全量子插件加载 **7/7**；`config.yaml` 与 `config.example.yaml` 均过 `PluginConfig` 校验；真实 `GraphPipeline` 端到端 `ainvoke`（真插件 + 真 config + 替换掉实例化来源的假模型）—— `build_client` 收到 `model=deepseek-flash` / `base_url` / `api_key` / `max_tokens=4096`，管理员可见 15 个工具、路人可见 9 个，`system_prompt` 已注入账号信息，`final_answer` 正常产出。**未验证**：NcatBot 运行时下的端到端（`on_message` → 发送循环）未跑；`_compact.py` 的 `CONTEXT_WINDOW` 仍是硬编码 `128000`。**已知边界**：模型选择仍是「取根配置里第一个供应商的第一个模型」（`main.py` 内标 `# HACK`），尚未提供配置项。

v0.9.10 — **`_dispatch` 加错误处理，并新增 `PipelineStopDispatch` 停止分发信号**：此前 `_dispatch` 明确标着「先不写错误处理」（`# NOTE`），handler 里抛任何异常都会直接冒到 langgraph。现在每个 handler 被 `try` 包住，分三类处理 —— ① `PipelineStopDispatch` → `break`，**停止本事件剩余 handler**（已累积的增量照常返回，后续事件不受影响）；② `langgraph.errors.GraphBubbleUp`（含 `GraphInterrupt` 等 langgraph 控制流）→ 原样 `raise`，保证中断/命令语义不被误吞；③ 其它 `Exception` → `LOGGER.exception(...)` 记录 traceback 后 `continue`，**跳过该 handler 继续执行本事件剩余 handler**（注意：这与旧行为不同，旧行为是直接冒到 langgraph）。同时清理：删除已无用的 `APIUnavailableError`（`errors/api_unavailable_error.py`），根包与 `errors` 包的导出表同步。**验证**：真实 `GraphPipeline` 实测 —— priority 100 的 handler 增量在 stop 后**被保留**、priority 50 抛停后 priority 0 的 handler **被跳过**、同一请求的后续事件（`ON_AGENT_END`）**照常执行**且图正常完成；对照实验确认普通异常（`ValueError`）**不再冒泡**而是记录后跳过、本事件后续 handler 照常跑完。**未验证**：`PipelineStopDispatch` 尚无实际业务消费方；**另外修复 `attach_image` 的优先级倒挂**：它原为 `priority=10` 而 `invoke_tools` 为 `0`，dispatch 降序执行使它在 `invoke_tools` **之前**跑，永远扫不到本轮工具消息、图片搬运逻辑完全空转；改为 `priority=-10` 后排在执行之后，实测图片已能从 `ToolMessage` 搬进 `HumanMessage`。NcatBot 运行时下的端到端未跑。

v0.9.8 — **发送循环加调试日志 + 变量语义化更名**：`on_message` 的发送段把图返回值改称 `raw_output`、正文提为 `answer_string`、切块结果提为 `answer_chunks`、循环变量改称 `chunk`，并在发送前加两条 `logger.debug`（本次输出字符数、分隔符与切出的块数），便于排查「一条回复被发成几条」类问题。**顺带修掉一次改名遗漏**：`answer_chunks` 误写成引用已不存在的 `raw_ot`（`NameError`，每条消息都会崩），已改为直接复用 `answer_string`。**验证**：AST 扫描确认无未定义名；模拟两种分隔符场景（`None` → 1 块、`"\n\n"` → 2 块）打印与发送条数正确；全仓 `compileall` 通过。**注意**：`logger.debug` 默认级别为 INFO，且你的 `/sdcard/Ncatbot_QQ/config.yaml` 是 `debug: false` + `logging.log_level: "ERROR"` —— 当前配置下这两条日志不会输出，需要 debug 模式才会显示。

v0.9.7 — **修复「未设置分隔符时回复被逐字拆成 N 条消息」**：`on_message` 的发送循环此前是「有分隔符 → `.split()` 得到 list，无分隔符 → 直接用整个 `str`」两条分支混进同一个 `for` —— 当 `output.split_separator` 为 `null`（默认值）时 `for answer in final_answer` **迭代的是字符串本身，即逐字符**：一句话被拆成几十条 QQ 消息逐字发出，且每个字符都要 sleep 一次打字延迟。现已把切块收口到新增的 `utils.split_string`（**恒返回 `List[str]`**：无分隔符 / 空串 → `[整条]`，否则 `str.split`），`for` 拿到的必然是「块」而不是「字符」。实测同一段 13 字文本：修复前发出 13 条、修复后 1 条。**验证**：`split_string` 五种分隔符真跑（`None` / `""` / `"\n\n"` / `"||"` / 单字）+ 空串输入边界，恒返回 list；`utils/sugar.py` 补齐 `Optional` / `List` 类型导入（此前靠 Python 3.14 注解延迟求值侥幸不报错，`typing.get_type_hints` 会 `NameError`）；`concatenate_id` 签名去掉了多余的 `is_group` 默认值（唯一调用处本就显式传参）；全仓 `compileall` 通过。**未验证**：NcatBot 运行时下的真实 QQ 发送未跑。

v0.9.6 — **新增 `tool_permission_manager` 子插件（工具级权限控制）**：按自带 `config.yaml` 的权限表（`admin` / `white_list` / `anyone` 三种），在 `ON_BEFORE_REQUEST`（`priority=1`）把当前身份无权使用的工具从 `runtime.context["tools"]` 摘掉 —— 摘掉后 `call_llm` 与 `invoke_tools` 两侧都拿不到（模型看不见、执行器也拿不到），未声明的工具默认拒绝并打 warning。配套补齐 `base_system_tools` 与 `tool_permission_manager` 两份子插件 `README.md`（前者只讲工具用途，权限说明移交给后者）。**破坏性**：主包配置模型的 `account` 字段改名 —— `root_id` → `admin_id`、`root_nickname` → `admin_nickname`（模型文件 `models/config/accounts.py` → `account.py`、类名 `Accounts` → `Account`），根 `config.yaml` / `config.example.yaml` / `format_prompt` 节点同步。**验证**：15 个真实注册工具逐字比对权限表（无漏声明 / 无多余条目 / 无重复）、`Permission` 三种分支单测、真实 `GraphPipeline` 端到端确认摘除确实传到下游请求节点、`config.example.yaml` 过 `PluginConfig` 校验。**未验证**：warning 去重（用户明确不做）、插件整体在 NcatBot 运行时下的端到端对话未跑。

v0.9.5 — **子插件文档补齐**：`base_system_tools` 新增 `README.md`，列清 5 个系统工具（`bash` / `read_file` / `read_image` / `replace` / `write`）并**明确写出当前的安全缺口** —— 所有工具都没有管理员校验、数据完全公开，权限控制后续再加入；与 `meme_extension` 的隐私提示同一思路（把风险写在插件自己家门口）。**验证**：README 里 5 个工具名与 `tools/__init__.py` 的导出、各 `@tool(args_schema=ToolSchema)` 函数名逐一对照（5/5，无遗漏无多余）；「无管理员校验」对照全目录 `grep`（`admin` / `permission` / `权限`）零命中，声明属实。**未验证**：权限控制仍未实现（README 中标注为后续计划），本版无代码改动。

v0.9.4 — **image 段解析新增 `is_meme`，并收窄到 QQ 平台**：`image_parser.py` 更名 `qq_image_parser.py`、`ImageSegmentParser` 更名 `QQImageSegmentParser`，`is_accept` 从 `isinstance(data, Image)` 收紧为 `isinstance(data, QQImage)`（`QQImage` 声明 `sub_type: int = 0`，于是 `handle()` 不必再 `getattr` 兜底），返回体从 `{image, size}` 变为 `{image, size, is_meme}`（`is_meme = bool(data.sub_type)`，非 0 视为表情包），让模型能区分表情包与用户发的普通图片；子插件 `meme_extension` 新增 `README.md`，写明「模型可能把普通图片误归档成表情包」的隐私风险；`base_system_tools/tools/bash.py` 删掉一段已无意义的进程泄漏 NOTE 注释（纯注释，行为未变）。**验证**：七种形态真跑（`sub_type=1` / `=0` / 缺键 / 驼峰 `subType` / 缺 `url` / common `Image` / 直接构造），`is_meme`、`url` 回退与拒收行为均符合预期，全程无日志输出；旧类名/旧模块名无残留引用。**已知限制**：只认 QQ 平台 —— 非 QQ 适配器下的 image 段会无人 accept，`segments` 里会出现 `null`；驼峰 `subType` 与「上游不发 `sub_type`」都静默为 `false`（已按「确认不会缺」的决定去掉日志）。**未验证**：`is_meme` 进提示词后的识别效果与真机 `sub_type` 取值分布。

v0.9.3 — **补齐 `langchain-core` / `pydantic` / `pyyaml` 三个依赖声明**：这三个包本插件都是直接 import（`@tool` 工具定义、配置层 `BaseModel` / `Field`、`core/plugin_loader.py` 的 `yaml.safe_load`），却一直靠 `ncatbot`（pydantic / PyYAML）与 `langgraph` / `langchain-openai`（langchain-core）的传递依赖混进来 —— 上游一旦改依赖树，本插件就会在导入期 `ModuleNotFoundError`；`pip_dependencies` 10 → 13，版本下限取当前环境实测版本（1.6.5 / 2.13.5 / 6.0.3）。**验证**：`ast` 扫全仓顶层绝对 import 对照清单，未声明项归零（0.9.2 时还剩这三个）；`manifest.toml` 经 `tomllib` 解析通过（0.9.3 / 13 项）。**未验证**：插件整体 `on_load` 与各子插件在 NcatBot 运行时下的端到端调用未跑。

v0.9.2 — **补齐 `aiofiles` 依赖声明**：子插件 `base_system_tools` 的 `write` / `replace` 两个工具一直用 `aiofiles` 异步写盘，`manifest.toml` 却没声明它 —— 开发机环境里恰好装着所以没暴露，干净环境会在子插件导入时 `ModuleNotFoundError: aiofiles`（0.9.0 起 `load_all()` 一处抛错会连带排在后面的子插件一起不加载）；`pip_dependencies` 9 → 10（`aiofiles >=24.1.0`）。**验证**：`ast` 扫全仓顶层 import 比对清单，`aiofiles` 已消除；两个工具端到端跑通（写入落盘 / 全量替换 / `count=1` 只换第一处 / `encoding=gbk` 读写 / 目标不可写返回 `fail` 而不抛）。**未验证**：`base_system_tools` 在 NcatBot 运行时下的工具端到端调用未跑。**仍缺声明（本次未动）**：`langchain_core` / `pydantic` / `yaml` 也是直接 import 但未声明，目前靠 `ncatbot` / `langgraph` / `langchain-openai` 的传递依赖进来。

v0.9.1 — **meme 子系统的 sqlite 驱动换成 `aiosqlite`**：`rapsqlite` 在 x86_64 上没有预编译轮子（要现场编译），而 `MemeSqlite` 用到的能力 `aiosqlite` 全都有 —— `plugins/meme_extension/core/meme_sqlite.py` 改为 `import aiosqlite`，建连从 `__init__`（`rapsqlite.connect` 是同步的）挪到 `__aenter__`（`await aiosqlite.connect(self.path)`，在 DDL 之前），`manifest.toml` 移除 `rapsqlite`（`pip_dependencies` 10 → 9，`aiosqlite` 由 `SQLiteAdapter` 与 `MemeSqlite` 共用）；对外接口与 `async with` 用法不变。**验证**：对真实 sqlite 文件跑通 `MemeSqlite` 全部接口（建表 / 索引 / 外键 / 插入 / 判重 / 列全部 / 按 hash 取 / 按标签查含多标签交集 / 按 hash 删 / 级联清 tag）并跨 `async with` 重开确认落盘，14 项断言全 PASS。**未验证**：`meme_extension` 在 NcatBot 运行时下的工具端到端调用未跑。

v0.9.0 — **checkpointer 真正接线 + 内置子插件入仓**：`config.yaml` 的 `checkpointer.database` 现在能在 `memory` / `sqlite` / `postgresql` 之间切换 —— 新增 `protocols/abc/checkpointer_adapter.py` 的 `BaseCheckpointerSaverAdapter`（`ABC + BaseCheckpointSaver`，1:1 转发 `get_tuple` / `list` / `put` / `put_writes` / `delete_thread` / `delete_for_runs` / `copy_thread` / `prune` 与对应的 8 个异步方法，以及 `config_specs` / `get_next_version` / `with_allowlist`；抽象 `connect(connect_to, **kwargs)` / `close()`）与 `adapters/check_pointers/` 的三个实现（`InMemoryAdapter` / `SQLiteAdapter` = `aiosqlite` + `AsyncSqliteSaver` / `PostgresqlAdapter` = `AsyncConnectionPool` + `AsyncPostgresSaver`）；`main.py` 新增 `CPA_MAPPING` 按 `database` 取类，`_build_graph(checkpointer)` 不再写死 `InMemorySaver()`，`on_close` 改为 `await self.cpa.close()`；配置键 `check_pointer` → `checkpointer`（**破坏性**）并新增 `extra`（透传 `connect(**kwargs)`）；`Closable` 协议与 `main.MiaoLiBot.clean_share_store()` 兜底清理整体移除（由显式 `close()` 取代）；五个内置子插件从 `/sdcard/python/miaoli_bot_plugins` 迁入本仓库 `plugins/` 并随仓库提交（`.gitignore` 增加 `!plugins/*/config.yaml` 例外，子插件默认值入库）。**验证**：memory / sqlite 端到端跑通；postgresql 对真库（`127.0.0.1:15432/miaoli`，PostgreSQL 14.24）跑通 26 项断言 —— 建表与重复 `setup` 幂等 / 两轮续存真落库 / `aget_state_history` 与 `parent_config` 链 / `adelete_thread` 清理后归零 / `close()` 关池 / 同步路径 `InvalidStateError` 原样透传 / `prune` 等三个 `NotImplementedError` 透传 / `extra` 参数（`max_size` / `min_size` / `row_factory`）确实落到池上。**未验证**：插件整体 `on_load` 未在 NcatBot 运行时跑过（只验证了 `PluginConfig` 校验 + `CPA_MAPPING` 建连 + `MiaoLiBot._build_graph(adapter)` 能 `compile`），`plugins/` 五个子插件未做运行验证。**仍遗留**：`sub_plugin.is_enable` 未被消费、`PluginLoader` 对 `load_from=None` 无明确行为、`main.py` 的 `chat_model` 仍是 `# HACK`。

v0.8.3 — **meme 子系统整体迁出主包（架构级变更）**：`tools/`（`meme_ops` 的 `send_meme` / `archive_meme` / `list_memes`）与 `utils/meme_sqlite.py` 删除，`MemeConfig` 配置模型与 `meme` 配置键移除，meme 能力改由新增的内置子插件 `meme_extension` 提供（`archive_meme` / `send_meme_to_qq` / `list_memes` / `remove_meme_by_hash` / `search_memes_by_tags`）；修复两处 0.8.2 遗留问题 —— `PluginConfig` 补齐 `CheckPointerConfig` 导入（不再 `NameError`）、`OutputConfig.split_separator` 改为可空并在 `main.py` 增加 `None` 分支（不切块、整条发送）；另将 `GraphPipeline` 的 handler 排序改为按 `priority` 降序，`base_nodes` 的注册优先级相应调整（`compact` = 1、`attach_image` = 10）。**仍遗留**：`check_pointer` 尚未接线（`main.py` 写死 `InMemorySaver()`）、`sub_plugin.is_enable` 未被消费。

v0.8.2 — **插件化拆分（架构级变更）**：图节点与两级解析器从主包移出、改由子插件在运行时注册 —— 新增 `core/plugin_loader.py`（`PluginLoader`：扫 `plugin.toml` → 注册成包 → 加载 / 卸载）、`core/registry.py`（`Registry`：子插件的工具 / 解析器 / 图节点注册门面）与 `core/tool_registry.py`（`ToolRegistry`，替代硬编码 `TOOLS`），`main.py` 随之瘦身为「建容器 → 建图 → `load_all()`」；`parsers/`、`core/nodes.py`、`tools/` 下 5 个平台工具删除，`models/plugin_config.py` 拆成 `models/config/` 包、`models/runtimes/` 更名 `models/runtime/`、`protocols/` 拆成 `abc/` 与 `runtime/` 两个子包；配置键 `account_config` / `meme_config` / `output_config` 更名为 `account` / `meme` / `output` 并新增 `check_pointer`（`CheckPointerConfig`），`manifest.toml` 依赖新增 `filetype`；`output` 三个字段落地消费（切块 + 打字延迟）。**随附四个内置子插件**：`base_nodes`（图节点，另含上下文压缩与图片附加）、`base_parsers`（解析器）、`base_platform_tools`（发消息 / 发文件 / 下载 / 查 ID / 撤回）、`base_system_tools`（bash / 读写文件 / 读图）。**Future：让 `config.yaml` 动态切换数据库，并为此新增 `check_pointer` 适配器（把 `database` / `connect_to` 映射到 `InMemorySaver` / `AsyncSqliteSaver` / `AsyncPostgresSaver`）。待优化项：`main.py` 的 `chat_model` 仍每条消息 new 一个 `ChatOpenAI`（标 `# HACK`，未接 `providers`）；`MemeConfig` 待随 `tools` 迁到子插件（标 `# TODO`）；`GraphPipeline._dispatch` 无错误处理（标 `# NOTE`）；子插件 `_compact.py` 的常量与 token 估算待配置化。** 另：`CheckPointerConfig` 模型已就位但尚未接线（`plugin.py` 缺 import，当前导入会 `NameError`）。

v0.8.1 — **meme 子系统落地 + 工具层参数收口（含三处破坏性更名）**：删除 `core/meme_manager.py` 与 `utils/meme_sqlite_ops.py`，新增 `utils/meme_sqlite.py` 的 `MemeSqlite`（`rapsqlite` 异步驱动，`async with` 内建 `memes` / `tags` 两表 + 自动 `commit` / `close`，接口 `query_tags` / `fetch_memes` / `fetch_meme_from_hash` / `is_hash_existing` / `insert_meme`），`manifest.toml` 依赖新增 `rapsqlite`；`list_memes` 由 `fail("工具未写完")` 落地为 `{meme_id: {hash, description}}`。**破坏性更名**：配置键 `meme_config.sqlite_path` → `db_path`、`send_file_to_qq` 的参数 `file` → `path`（类型收紧为 `FilePath`）、`send_meme_to_qq` 的参数 `path` + `by` → `hash_`（不再按路径发图 —— 「已归档的表情包」与「任意文件」分属两个工具，避免模型选错）。修复：`Image(url=…)` 参数名写错（`Image` 的必填字段是 `file`，报 `file: Field required`）、base64 两处 bytes（`b64encode` 与 sqlite 取出的都是 bytes，拼出 `base64://b'…'` 需 `.decode()`）、`archive_meme` 对 dict 解包拿到键名、`fetch_meme_from_hash` 缺 `hash` 键、`MemeSqlite.__aexit__` 签名与漏 `close()`、`is_hash_existing` 恒真、`fetch_memes` 缺 `def`、两处 SQL 语法错、两处漏 import、两处命名。**架构未动，仍处优化态**。

v0.8.0 — **移除 `pi_bridge`，改用 LangGraph 自建图管线（破坏性重构）**：删除 `core/pi_client.py` / `pi_session_manager.py` / `pi_tool_backend.py` / `_prompt.py`、`utils/pi_event_classifier.py`、`errors/miss_factory_error.py` / `pi_prompt_busy_error.py` 与 `enums/` 目录，`manifest.toml` 的依赖改为 `langgraph` + `langchain-openai`；新增 `core/graph_pipeline.py`（`GraphPipeline`：`register(event, node, priority)` 显式挂载 + `wire()` 一次成型 + `_dispatch` 按优先级串行并对返回值做增量合并）、`consts/graph.py`（8 个图事件 + `MAX/MIN_PRIORITY`）、`core/nodes.py`（5 个节点）、`models/graph_state.py`（进 checkpoint 的会话状态）与 `models/graph_runtime_context.py`（不进 checkpoint 的运行时依赖）；`PluginConfig` 重构为分层结构（`providers` / `account_config`（必填）/ `meme_config` / `output_config` + `session_dir` / `prompt_file` / `system_prompt`），**配置结构与共享键均不向下兼容**（`plugin_configs.miaoli_bot` 需整块重写）；工具由 4 个扩到 8 个（新增 `send_file_to_qq` / `send_meme_to_qq` / `list_memes` / `archive_meme`），返回值统一走 `utils.tool_result_builder`；`config.yaml` 改由 `config.example.yaml` 作入库模板；`parsers` 的 `file_parser` 返回值键由 `image` 修正为 `file`（**破坏性**）；`main.py` / `models` / `utils` / `consts` / `errors` 的导出表全部同步。**重构完成，进入优化态**，后续迭代项：`OutputConfig` 是预留占位（字段已定、暂无消费方，见 CHANGELOG 0.8.0 的 Note）；`main.py` 的 `chat_model` 仍是每条消息 new 一个 `ChatOpenAI` 的 `# HACK`；`GraphPipeline._dispatch` 暂无错误处理、`_build_graph` 写 `SHARE_STORE` 未持 `store_lock`；本地 147 例用例整体失效待重写。（另：三处漏 import 的注解 `Union` / `List` 已补齐 —— Python 3.14 的注解延迟求值让「漏 import 类型」不再报 `NameError` 而是静默失效，只有 pydantic 这种必须解析注解建 schema 的使用方才会炸，详见 CHANGELOG 0.8.0 的 Note。）

v0.7.0 — **配置模型化（pydantic）+ 共享键拆分**：新增 `models/plugin_config.py` 的 `PluginConfig`（字段 `model_id` / `provider` / `session_dir` / `system_prompt` / `prompt_file`，`extra="allow"` 放行额外键），`on_load` 里 `PluginConfig.model_validate(self.config)` 把 ncatbot 合并后的配置转成模型实例存入 `self.cfg`；配置键名随之对齐模型字段（`default_model` → `model_id`、`default_provider` → `provider`、`pi_system_prompt` → `system_prompt`，**破坏性变更**，`config.yaml` 已同步）；共享容器的 `PLUGIN_CONFIG` 由「原始 dict」改为「`PluginConfig` 实例」，原始 dict 改存新增的 `RAW_CONFIG` 键（`on_close` 两键都显式 `drop`）；`create_pi_factory` 与 `PIToolBackend` 相应改为按属性取值。配置校验前移到加载期（必填缺失即 `ValidationError`，不再等到首条消息 `KeyError`），提示词读盘从「每条消息」变为「加载时一次」，本地测试 147 例通过。遗留：`buffer_limit` 仍是 extra 键（无类型校验与默认值保护），运行期 `set_config()` 不会重解析 `self.cfg`（需重载插件）；`core/_prompt.py` 仍为 WIP；`RequestRefuseError` 仍未捕获（见 v0.5.4）。

v0.6.0 — **配置化建会话 + 关闭兜底清理**：建连参数由 `on_message` 内的硬编码改为 `config.yaml` 驱动（`session_dir` / `buffer_limit` / `prompt_file` 或 `pi_system_prompt` / `default_provider` / `default_model`），`create_pi_factory(session_id)` 产出无参工厂供 `ensure_session` 惰性调用；`PiSessionManager` 的 `close_sessions()` 更名为 `close()`、`ensure_session(create_timeout=…)` 更名为 `timeout=…` 且 `factory` 变为可选（未命中且缺省抛新增的 `MissFactoryError`）—— **两处更名为破坏性变更**；`on_close` 改由 `clean_share_store()` 经新增的 `Closable` 运行时协议统一兜底清理 `SHARE_STORE`（显式清理仍是第一责任）。群 / 私聊对话、工具调用与兜底清理路径均已端到端验证。遗留：`create_pi_factory` 未做配置校验（`default_provider` / `default_model` 缺失会在建连时 `KeyError`，计划换 pydantic 动态配置模型）；`core/_prompt.py` 为未接入 `PiClient` 的 WIP；`RequestRefuseError` 仍未捕获（见 v0.5.4）。

v0.5.4 — **`pi_bridge` 依赖下限提到 `>=0.6.0`**：0.6.0 是行为变更版本（`PiClient.prompt` 请求被拒时由「静默零事件」改为抛 `RequestRefuseError`；`PIProcess.build` 的 `session` 参数更名为 `session_id`）；本插件经 `PiClient.open(session_id=…, …)` 建连，不受参数更名影响。**暂未捕获 `RequestRefuseError`** —— PI 拒绝时异常会冒到 ncatbot 事件处理器（日志有 traceback、用户侧无回复），留待后续处理。

v0.5.3 — **事件优先级让位，修复插件命令重复响应**：`on_message` 由默认优先级改为 `priority=-100`（`main.py`），让扩展插件先处理消息；`miaoli_like` 的 `赞我` 命令以 `priority=100` 抢先接收，并置 `event.data._propagation_stopped = True` 停止传播，该消息不再进入 LLM —— 修复私聊中发送 `赞我` 时本插件也回复一次的重复响应。跨插件协作已在真实 QQ 环境手动验证。

v0.5.2 — **关闭流程重构**：`close_sessions` 把「取快照 + 清空缓存」下沉为同步方法 `_pop_sessions()`（普通 `def`，语言层面保证中间不可能插入 `await`），幂等语义仍留在 `close_sessions`，对外行为与 0.5.1 一致；`_locks` 字典按设计保留不清理（清理会让同一 `session_id` 出现两把锁，实测并发建出两个 client 并产生孤儿，代价仅约 105 B/会话且随实例回收）。并发用例增至 16 例、全量 102 例通过。

v0.5.1 — **关闭窗口泄漏修复**：`ensure_session` 在工厂返回后、写缓存前再判一次 `_is_closing`，回收「已通过判定、在关闭期间才建好」的 `PiClient` 并抛 `SessionManagerClosingError`（关闭中不再留下永不 `close` 的会话），进锁前的前置判定保留作快速失败门槛；本地测试目录由 `test/` 更名为 `tests/`（`.gitignore` 同步），并新增 `PiSessionManager` 高并发用例（同会话单例 / 会话隔离 / 失败路径 / 关闭幂等 / 关闭窗口回收，14 例，全量 100 例通过）。用例覆盖的是并发不变量，与真实 PI 进程 / 网络环境下的并发行为不等价。

v0.5.0 — **会话隔离落地**：新增 `PiSessionManager`（`core/pi_session_manager.py`）按会话管理 `PiClient`，会话键 = `group-` / `private-` 前缀 + 目标 id（`utils.sugar.concatenate_id` + `consts/id_prefix.py`），`ensure_session` 命中复用、未命中建连并缓存，`close_sessions` 幂等关闭（关闭中请求抛 `SessionManagerClosingError`）；`on_load` 不再创建全局单例 client（移除原 HACK 技术债），改注册 `PI_SESSION_MANAGER` 共享键并在 `on_close` 关闭全部会话。群聊 / 私聊的建会话与正常对话已手动验证（各会话独立、无串台），**但 SessionManager 在并发场景下的稳定性尚未验证**。Future：让 `PiClient.prompt` 返回可遍历的 `Prompt` 对象并支持事件回调注册，替代调用方 `async for` + 一串 `if` 的分支写法。

v0.4.0 — 新增 `delete_qq_message` 撤回消息工具（`tools/delete_message.py`，`tools/__init__` 导出并在 `main.py` 注册进 `PIToolBackend`）；`on_load` / `on_close` 补充插件上下线日志；`on_message` 事件循环不再在 agent 结束后 `break`，未处理事件改为 warning 记录；`utils/easier_sender.py` 移除未使用的 `*args` / `**kwargs` 透传；本地测试目录由 `pytest/` 更名为 `test/`（`.gitignore` 同步）。

v0.3.3 — 新增 `PiClient.is_streaming` 只读属性（直接返回 `_stream_lock.locked()`，提供不经 RPC 的本地忙闲查询入口）；`main.py` 移除未使用的 `get_log` 导入。

v0.3.2 — 插件入口类改名为 `MiaoLiBot`（原 `Claw`），`manifest.toml` 的 `entry_class` 同步更新，**本次为纯改名，无 API 变动**；同时为 `on_message` 的消息段取值增加空值防护（`getattr(event, "message", None)` + 判空提前返回）。

v0.3.1 — 客户端侧单订阅者互斥落地：`PiClient` 引入 `asyncio.Lock`，忙闲判定由一次 `get_state()` RPC 往返改为本地锁检查，消除 TOCTOU 窗口；`prompt` 签名收紧为显式参数，忙时未指定 `streamingBehavior` 抛 `PIPromptBusyError`（新增 `errors/` 异常模块）；崩溃落盘逻辑移除并改用 `PI_LOGGER.exception()`（覆盖率由 `ValueError` 扩大到全部异常，自带 traceback），同步移除 `aiofiles` 依赖。
