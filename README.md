# miaoli_bot

[English](README/en.md) | **简体中文**

一个基于 [Ncatbot](https://github.com/NapNeko/NcatBot) 的 QQ 机器人插件，用 **LangGraph** 自建图管线把 QQ 对话接给 LLM，让 QQ 消息驱动模型思考、回复并调用工具。

- **版本**：0.36.0
- **入口**：`main.py`（插件类 `MiaoLiBot`）
- **运行载体**：Ncatbot 插件系统（NapCat/OneBot 协议）
- **LLM 客户端**：`providers[].client` 选 `ChatOpenAI`（`langchain-openai`）/ `ChatDeepSeek`（`langchain-deepseek`）/ `ChatAnthropic`（`langchain-anthropic`），统一经 `miaoli_bot.api.build_client()` 构建
- **阶段**：插件化拆分完成，当前处于**优化态** —— 现状与已知短板见[项目状态](#项目状态)
- **默认跳转**：edgeless 拓扑下「下一个事件是谁」由处理器主动声明，`default_routing` 子插件提供默认顺序（**一个事件一个节点文件**，每个只返回一条 `Goto`），并承担 `ON_AFTER_REQUEST` 的分支判断（末条有 `tool_calls` → 工具循环，否则 → 收尾），以及压缩三段的默认路径（`ON_BEFORE_COMPACT` 默认不压缩直接去 `ON_BEFORE_REQUEST`，`ON_AFTER_COMPACT` 跳回 `ON_TURN_START`）。它注册在**最低优先级** `MINIMUM`，任何子插件挂在任何更高档位都能抢在它之前改道或叫停

## 功能特性

- 🧩 **事件管线（edgeless 拓扑，已独立成包）**：`GraphPipeline` 由独立依赖 [`miaoli_pipeline`](https://github.com/lyt2011/miaoli_pipeline) 提供（泛型 `GraphPipeline[StateT, ContextT, InputT, OutputT]`，四个 TypeVar 取自 `langgraph.typing`），本仓库只保留事件名与注册门面 —— 11 个图事件常量集中在 `consts/graph_events.py`，节点用 `register_handler(event, node, priority=0)` **显式**挂载（同一事件可挂多个，按 `priority` 降序执行，`priority` 大者先跑；档位常量是 `consts/node_priorities.py` 的九档阶梯 `MAXIMUM`(9999) … `NORMAL`(0) … `MINIMUM`(-9999)）。`wire()` **不定义任何事件顺序**，只挂事件节点 + 一条入口边（`START → ON_AGENT_START`）；「下一个事件是谁」由处理器**主动返回跳转指令**决定：`return {...}` 累积增量并继续本事件剩余处理器、`Continue(updates=…)` 停止本事件剩余处理器、`Goto(goto=…, updates=…)` 跳到指定事件、`Abort(reason=…, updates=…)` 中止整轮图。**谁挂在哪个事件上、谁跳向哪里，都由子插件注册时声明**。
- 🔌 **子插件系统**：`core.Loader` 读 `sub_plugin.load_from`（`List[Path]`，可给多个目录）下每个子目录的 `metadata.toml` 建 `Plugin`（缺元数据直接抛错、非包目录跳过），再按 `tp_sort()` 的依赖序逐个「注册成 Python 包 → 实例化 `entry_class` → 注入 `workspace` / `metadata` / `config` → `on_load()`」；单个插件 `on_load` 失败只记日志并把自己从 `sys.modules` 抹掉。子插件用 `HandlerRegistry.on_*()` 挂图节点、`ToolRegistry.register()` 注册工具，卸载时在 `on_close` 里用对应的 `HandlerRegistry.remove_*()` / `ToolRegistry.remove()` 逐一摘回来（不摘就会在下一次加载时重复挂载）；卸载走 `deactivate()`（转发 `on_close`）→ `unload()`（清 `sys.modules`），改完代码重载立即生效。
- 🧠 **LLM 接入**：`main.py` 只把 `event` 写进 state；`miaoli_bot_adapter` 子插件的 `inject_soul` / `inject_output_protocol` 节点（`ON_TURN_START`，`priority=NORMAL+1`）分别读子插件自己目录下的 `data/SOUL.md` 与 `data/output_protocol.md`，写进 `prompts` 的 `soul` / `output-protocol` 段，随后 `build_client` 节点（`priority=NORMAL`）调 `miaoli_bot.api` 的 `build_client()` 从根配置直接建客户端（具体类由 `providers[].client` 选）写进 `runtime.context["client"]`（**刻意不在建实例时绑工具** —— 工具表按身份每请求变化）；`call_llm` 节点用 `runtime.context["tools"]`（来自 `ToolRegistry`）`bind_tools` 后请求模型；工具循环由 `default_routing` 的 `on_after_request` 节点分流 —— 末条消息有 `tool_calls` 就跳 `ON_TOOL_CALLING` 执行工具、再回到 `ON_TURN_START` 重走一轮；没有就跳 `ON_TURN_END` 收尾。
- 🗜️ **上下文压缩（三段事件）**：压缩不再是藏在 `on_before_request` 里的一个 `if`，而是图上三个有名字的事件 —— `ON_BEFORE_COMPACT` 挂**守卫** `should_compact`（`context_compactor` 子插件，`priority=NORMAL`）算 token 判阈值，需要压就 `Goto(ON_COMPACT)`、不需要就 `Goto(ON_BEFORE_REQUEST)`；`ON_COMPACT` 挂**压缩** `compact`，把历史压成一条 `<abstract>` 摘要并用 `Overwrite` 整体替换；`ON_AFTER_COMPACT` 的默认跳转**回到 `ON_TURN_START`**，于是压缩完重新走一轮（这一轮守卫命中 `<abstract>` 标志后 `Abort`，本轮结束）。阈值按模型真实 `context_window` / `max_tokens` 算（为输出预留空间），保留条数 / 提示词 / 计数方式（`base` 粗估或 `tiktoken` 精确）全部配置化；压缩提示词内置在 `plugins/context_compactor/utils/prompt_ops.py` 的 `DEFAULT_PROMPT`，`compact.prompt_file` 可覆盖，且守卫估算 token 时会把这段提示词一并计入。
- 📝 **提示词分段拼装**：`prompts` 不是一整个字符串，而是 `Dict[str, str]` —— 各子插件写各自的段（`{"identity": …}` / `{"style": …}`），写入 `None` 表示删除该段。`prompt_builder` 子插件的 `build_prompt` 节点（`ON_BEFORE_REQUEST`，`priority=NORMAL+1`）把全部段拼成 `<key>value</key>` 形式，用 `Overwrite` 放到 `messages[0]`；内容与现有首条 `SystemMessage` 完全相同时返回 `None`，不白写一次 `Overwrite`。
- 📜 **状态与运行时分离**：`models.GraphState`（会话状态：`messages` 用 `add_messages`、`prompts` 用 `SectionPatch`，两者**进 checkpoint**；`event` / `final_answer` 两键用 `Annotated[T, UntrackedValue]` —— 单次 `ainvoke` 内可见、**不落盘**）与 `models.GraphRuntimeContext`（不进 checkpoint 的运行时依赖：`client` / `tools`）分离 —— `context` 不做浅拷贝、结果保持原引用，所以 LLM 客户端 / 锁这类不可序列化对象只能放 `context`（放 state 会因 msgpack 无法序列化而当场崩）。
- 🎛️ **配置模型化（分层 + 更名）**：`PluginConfig` 含 `providers`（`List[Provider]`，每项用 `name` 字段标识 —— `Provider` 有 `name` / `base_url` / `api_key` / `client`（`openai` / `deepseek` / `anthropic`）/ `models`，而 `models` 是 `List[LLM]`、`LLM` 有 `name` / `context_window` / `max_tokens` / `support_visions`）、`provider` / `model`（两个名字，由 `model_validator` 校验确实存在于 `providers` 里）、`account`（`bot_id` / `admin_id` / `bot_nickname` / `admin_nickname`，四项全必填）、`split`、`typing`、`checkpointer` 与 `sub_plugin`。
- 🛠️ **工具调用闭环**：工具统一经 `ToolRegistry` 注册、由 `ToolNode` 执行。返回值目前**不统一**：`system_tools` 的读写工具返回纯字符串（失败时 `[..]` 包裹），平台 / meme / 联网工具仍是 `{"status": bool, ...}` 字典。主包不内置任何工具，平台 / 系统 / meme / 联网搜索工具全部由内置子插件注册；`tool_permission_manager` 子插件可在此基础上按身份做工具级权限控制（`on_before_request` 摘 `runtime.context["tools"]`，未声明即拒绝）。
- 🔍 **联网搜索**：`web_search` 子插件注册一个 `web_search` 工具（**工具名与后端无关**），`adapter` 选后端 —— 请求地址取自子插件 `config.yaml` 的 `api_url`（模板里 `langsearch` 为 `https://api.langsearch.com/v1/web-search`），原始响应整体交给模型。`adapter` 只影响工具的入参 schema 与返回数据形状，不影响工具名。实测**英文检索质量明显优于中文**（技术 / 包名类相关率约 65% vs 30%），工具 docstring 已要求模型优先用英文搜。
- 🖼️ **工具附件兜底**：部分模型不接受 `tool` 消息携带多模态块（无论块里是什么内容都会 `400` 或静默忽略），`tool_attachment_fixer` 子插件的 `fix_tool_attachment` 节点（`ON_TOOL_CALLING`，`priority=NORMAL-2`）把**非字符串**的 `ToolMessage.content` 整体挪进紧跟其后的一条 `HumanMessage`、原 `ToolMessage` 正文换成 `replace_text`；只对 `models` 里声明的模型生效，无改动时返回 `None` 不写增量。
- 🧩 **两级解析链**：`EventParseChain`（群 / 私聊事件元数据）与 `SegmentParseChain`（文本 / AT / 图片 / 文件 / 引用消息段）双链分发，由 `ob11_adapter` 子插件的 `event_adapter` 节点调起；解析器**完全吃字典**，不 import ncatbot 任何类。
- 🖼️ **多类型消息段**：`text` → `{text}`、`at` → `{at}`、`image` → `{image, size, sub_tp}`、`file` → `{file, size}`、`reply` → `{reply}`；解析器按段字典的 `type` 判别。
- 🔧 **协议先行**：抽象跟着所属层走 —— `PluginProtocol` 在 `core/plugin/protocols/`、`BaseCheckpointerSaverAdapter` 在 `core/check_pointer_adapters/protocols/`、`ChainProtocol` 在 `ob11_adapter/chains/`；原先独立的 `protocols/abc/` 目录与 `StoreProtocol` 已删除。
- 🗄️ **checkpointer 适配层**：`checkpointer.database` 在 `memory` / `sqlite` / `postgresql` 之间切换 checkpoint 存储 —— `core/check_pointer_adapters/` 的三个适配器把 `InMemorySaver` / `AsyncSqliteSaver` / `AsyncPostgresSaver` 收拢成同一门面（`core.check_pointer_adapters.BaseCheckpointerSaverAdapter`：1:1 转发 `BaseCheckpointSaver` 的同步 / 异步协议方法，`connect(connect_to, **extra)` 建连、`close()` 释放），`main.py` 的 `CPA_MAPPING` 按 `database` 取类，`on_load` 注入图、`on_close` 统一关闭。
- 💾 **共享存储**：`core/SHARE_STORE`（定义在 `core/_share_store.py`）全局共享容器；core 的键在 `consts/share_store_keys.py`（`NCATBOT_API` / `RAW_CONFIG` / `PLUGIN_CONFIG` / `PLUGIN_DIR` / `GRAPH_PIPELINE` / `WORKSPACE_DIR` / `TOOL_REGISTRY` / `HANDLER_REGISTRY`，共 8 个），子插件用自带命名空间键（如 `ob11_adapter` 的 `EVENT_PARSER` / `SEGMENT_PARSER` / `REGISTRY`）。
- 🚪 **`api/` 门面层**：子插件不直接碰 `SHARE_STORE`，统一从 `miaoli_bot.api` 取东西 —— 一个模块一类事：`account_ops`（账号信息）、`config_ops`（根配置对象）、`llm_ops`（`get_model_info` / `get_provider_info` / `build_client`）、`lock_ops`（会话级执行锁）、`pipeline_ops`（图管线）、`platform_ops`（`get_ncatbot_api`）、`registry_ops`（两个注册器句柄）、`store_ops`（存储操作），发送封装仍在 `utils.easier_sender`。好处是把「键名 + 取值路径 + 类型」这些内部细节锁在门面层里，子插件只依赖函数签名。
- 🧹 **导入分块与对齐**：模块顶部的导入按「`__future__` → 第三方 `from`（按顶层包名各成一块）→ 跨包自引用 `miaoli_bot.x` → 同包相对导入 `.` / `..` → 内置 `from` → 普通 `import`」排列，块与块之间空一行，块内按语句字符数从短到长；列对齐到组内最长前缀的下一个 4 的倍数（tab stop = 4），**换行导入是组尾** —— 它可以跟上面的行对齐，它下面的行另起一组。子插件只从主包的一层导入（`miaoli_bot.api` / `core` / `models` / `consts` / `utils`）。
- 🔔 **事件优先级让位**：`on_message` 以 `priority=-100` 注册，排在后处理的位置 —— 扩展插件可用更高优先级抢先接收并停止事件传播（如 `miaoli_like` 的 `赞我` 用 `priority=100`），被上游截下的消息不会再进入 LLM。
- 🎭 **人格与输出协议外置**：主包不再持有任何提示词资产 —— `data/prompts/` 目录、根配置的 `prompt_file` 与 `miaoli_bot.api` 的 `get_prompt` 都已删除。人格（`plugins/miaoli_bot_adapter/data/SOUL.md`）与输出协议（`plugins/miaoli_bot_adapter/data/output_protocol.md`）都是 `miaoli_bot_adapter` 子插件的资产，由 `inject_soul` / `inject_output_protocol` 每轮读盘写进 `prompts` 的 `soul` / `output-protocol` 段；`account_injector` 的 `inject_account` 只管管理员 / 机器人的 QQ 号与昵称，不碰人格。
- ⏱️ **输出切块与打字延迟**：`on_message` 按根配置 `split`（`enable` / `delimiter`）把回复切块，跳过空块；若 `typing.enable`，每块按 `len(块) * uniform(base_speed ± speed_offset)` sleep 后再发送，模拟真人在打字。发送由 `main.py` 负责：群聊首块走 `event.reply`（带引用），其余块与**私聊的全部块**走 `easier_send`。
- 🧪 **本地测试（待重写）**：`tests/` 目录（gitignore，不随仓库提交）里的用例针对的是 pi 桥接层，随 0.8.0 重构整体失效。

## 架构设计

```
QQ / NapCat (OneBot)
        │ ncatbot 事件
        ▼
main.py  MiaoLiBot(NcatBotPlugin)      ← config.yaml → models.PluginConfig（providers / provider / model / account / split / typing / sub_plugin / …）
        │   ① event._data.model_dump() + concatenate_id → session_id（thread_id）
        │   ② 群聊还要 @ 到 bot_id，否则跳过
        ▼
miaoli_pipeline.GraphPipeline.ainvoke({"event"}, thread_id=session_id, context=…)
        │
        │  START
        ▼
   ON_AGENT_START ── event_adapter（ob11_adapter：解析 event → event_data，回填 state["event"]，JSON 追加进 messages）
        │            inject_account（账号信息块 → prompt 的 account-info 段）
        ▼
   ON_TURN_START ── inject_soul / inject_output_protocol（data/SOUL.md、data/output_protocol.md → prompts 的 soul / output-protocol 段）
        │            build_client（根配置 → context["client"]，类由 providers[].client 选）
        ▼
   ON_BEFORE_COMPACT ── should_compact（算 token 判阈值）
        │                ├─ 不需要压缩 ──────────────────────┐
        │                └─ 需要压缩 → ON_COMPACT ── compact（压成 <abstract> 摘要，
        │                                              Overwrite 替换 messages）
        │                               └─▶ ON_AFTER_COMPACT ── 跳回 ON_TURN_START
        ▼◀──────────────────────────────────────────────────┘
   ON_BEFORE_REQUEST ── build_prompt（prompt 各段 → SystemMessage 放 messages[0]）→ pick_tools（按身份裁 tools）
        ▼
   ON_REQUEST ── call_llm ──▶ bind_tools(tools) → ChatOpenAI
        │                                              │
        │                                              ▼
   ON_AFTER_REQUEST ── default_routing: on_after_request（末条有 tool_calls？）
        │
        ├─ 有 tool_calls ──▶ ON_TOOL_CALLING ── invoke_tools（ToolNode → ToolMessage）
        │                                      └── 回到 ON_TURN_START（重走一轮）
        │
        └─ 无 tool_calls ──▶ ON_TURN_END ──▶ ON_AGENT_END ── output_checker（校验末条是 AIMessage）
                                                                └── latest_to_answer（messages[-1] → final_answer）
                                                                ▼
                                                               END

        │  final_state["final_answer"]（按 split.delimiter 切块 + typing 延迟）
        ▼
main.py  event.reply(群聊首块) / utils.easier_send(api, …)  ──▶  QQ
```

### 目录结构

```
miaoli_bot/
├── main.py                        # 插件入口：MiaoLiBot（建容器 + 建图 + 起子插件加载器）
├── manifest.toml                  # 插件清单（name / version / entry_class / pip_dependencies）
├── config.example.yaml            # 配置模板（config.yaml 已 gitignore，内含密钥不提交）
├── __init__.py                    # 顶层只重导出 api / core / models 三个入口
├── api/                           # 子插件唯一入口（门面层，不直接暴露 SHARE_STORE）
│   ├── account_ops.py             #   get_admin_id / get_bot_id / get_admin_nickname / get_bot_nickname
│   ├── config_ops.py              #   get_root_config（根配置对象）
│   ├── llm_ops.py                 #   get_model_info / get_provider_info / build_client（按 providers[].client 建客户端）
│   ├── lock_ops.py                #   get_invoke_lock（会话级执行锁）
│   ├── pipeline_ops.py            #   get_pipeline（图管线句柄）
│   ├── platform_ops.py            #   get_ncatbot_api（框架运行时句柄）
│   ├── registry_ops.py            #   get_handler_registry / get_tool_registry（两个注册器句柄）
│   └── store_ops.py               #   store_recall / store_drop / store_update / store_set / store_contains
├── consts/                        # 常量集中定义
│   ├── graph_events.py            #   11 个图事件名（ON_AGENT_START / ON_TURN_START / ON_BEFORE_COMPACT / ON_COMPACT / ON_AFTER_COMPACT / …）
│   ├── node_priorities.py         #   九档优先级阶梯（MAXIMUM 9999 … NORMAL 0 … MINIMUM -9999）
│   ├── id_prefix.py               #   会话键前缀（group- / private-）
│   └── share_store_keys.py        #   SHARE_STORE 键名（含 TOOL_REGISTRY / HANDLER_REGISTRY）
├── core/                          # 框架层：加载 / 注册 / 共享容器 / 适配器 / 调度器
│   ├── _share_store.py            #   SHARE_STORE：全局共享容器（_ShareStore 唯一实例）
│   ├── check_pointer_adapters/    #   checkpointer 适配器：InMemory / SQLite / Postgresql（+ protocols/ 的转发基类）
│   ├── plugin/                    #   子插件加载框架
│   │   ├── loader.py              #   Loader：prepare_plugins / load_plugins / unload_plugins
│   │   ├── plugin.py              #   Plugin：from_path / load / activate / deactivate / unload
│   │   ├── protocols/             #   PluginProtocol：on_load / on_close 两个生命周期方法
│   │   ├── models/                #   PluginMetadata / Dependence / Specifier
│   │   └── errors/                #   BasePluginError / NotAPackageError / MetadataMissingError / EntryClassNotFound
│   ├── scheduler/                 #   最小调度器：Job（func + timer）+ BaseTimer + Once / Every
│   └── registries/                #   两个注册器
│       ├── handler_registry.py    #   HandlerRegistry：事件 → 图节点注册（on / on_xxx + priority）
│       └── tool_registry.py       #   ToolRegistry：按名字存工具（register / remove / tools）
├── errors/                        # 异常定义（AgentAborted 已迁到 miaoli_pipeline.errors）
│   ├── base_bot_error.py          #   BaseBotError 基类
│   ├── client_not_found.py        #   ClientNotFound（没有与该客户端对应的适配器）
│   ├── model_not_found.py         #   ModelNotFound（供应商下没有声明的模型）
│   └── provider_not_found.py      #   ProviderNotFound（供应商未在配置中声明）
├── models/                        # 数据模型
│   ├── config/                    #   PluginConfig / Provider / LLM / Account / SplitConfig / TypingConfig / SubPluginConfig / CheckPointerConfig
│   ├── graph_state.py             #   GraphState（进 checkpoint 的是 messages 与 prompts；event / final_answer 用 UntrackedValue 不落盘）
│   └── graph_runtime_context.py   #   GraphRuntimeContext（不进 checkpoint：client / tools）
├── plugins/                       # 内置子插件（随仓库提交，加载目录由 sub_plugin.load_from 指定）
│   ├── account_injector/          #   账号注入节点（nodes/ + metadata.toml）
│   ├── base_nodes/                #   图节点（nodes/ + metadata.toml）
│   ├── system_tools/         #   系统工具（tools/ + models/ + consts/ + config.example.yaml + README）
│   ├── default_routing/             #   默认跳转（nodes/ 一个事件一个文件 + config.example.yaml）
│   ├── context_compactor/         #   上下文压缩（should_compact 守卫 + compact 压缩；nodes/ + utils/ 含内置提示词 + models/ + consts/ + config.example.yaml + README）
│   ├── time_injector/               #   每轮把当前时间写进 prompts 的 current-time 段（nodes/ + README）
│   ├── intent_recognition/        #   意图识别：按配置的规则匹配末条消息，命中就把对应提示词文件的内容拼成 intent-recognition 段（models/ + models/rules/ + protocols/ + nodes/ + utils/ + consts/ + config.example.yaml + README）
│   ├── mcp_adapter/               #   MCP 适配：接入外部 MCP server 并把其工具注入工具表（models/transports + nodes/ + config.example.yaml + README）
│   ├── meme_ops/                  #   meme 工具 + 使用提示注入（tools/ + nodes/ + core/ + models/ + consts/ + config.example.yaml + README）
│   ├── miaoli_bot_adapter/        #   人格与输出协议资产（inject_soul / inject_output_protocol；data/ + nodes/ + models/ + consts/ + config.example.yaml + README）
│   ├── ob11_adapter/              #   OB11 事件适配：两级解析器 + event_adapter（parsers/ + chains/ + api/ + nodes/ + models/ + consts/ + config.example.yaml + README）
│   ├── orphan_tool_fixer/         #   孤儿工具返回修复（nodes/ + utils/ + config.example.yaml）
│   ├── pending_tool_fixer/        #   悬空工具调用修复（nodes/ + utils/ + models/ + consts/ + config.example.yaml）
│   ├── prompt_builder/            #   提示词拼装：把 prompt 各段拼成 SystemMessage 放到 messages[0]（nodes/ + README）
│   ├── qq_platform_tools/         #   QQ 平台工具（tools/ + README）
│   ├── tool_attachment_fixer/     #   工具附件修复（nodes/ + utils/ + models/ + consts/ + config.example.yaml + README）
│   ├── tool_permission_manager/   #   工具权限控制（nodes/ + models/ + consts/ + config.example.yaml 权限表 + README）
│   └── web_search/                #   联网搜索（tools/ + models/ + consts/ + config.example.yaml + README）
├── tests/                         # 本地 pytest 用例（gitignore，不提交；当前待重写）
└── utils/                         # 工具函数
    ├── easier_sender.py           #   private / group 便捷发送封装
    └── sugar.py                   #   concatenate_id（会话键加 group- / private- 前缀）
```

## 数据流

1. QQ 消息经 NapCat → ncatbot → 按注册优先级分发给各插件：本插件以 `priority=-100` 排在后处理位置，上游插件若停下事件传播（如 `miaoli_like` 的 `赞我` 用 `priority=100`）本插件就收不到；群聊消息还必须 @ 到 `plugin_cfg.account.bot_id`。
2. `on_message` 先算 `is_group` / `chat_id` / `session_id`，再把 `event._data.model_dump()` 当作 `input["event"]` 传进图；解析在图内由 `ob11_adapter` 子插件的 `event_adapter` 完成（走 `EventParseChain` / `SegmentParseChain`）。
3. `session_id = concatenate_id(target_id, is_group=is_group)`（群 → `group-<group_id>`，私聊 → `private-<user_id>`），作为 LangGraph 的 `thread_id` —— 同一会话共享同一个 checkpointer（由 `checkpointer.database` 选中的 memory / sqlite / postgresql 实现）里的 checkpoint，跨轮记忆不串台。
4. `graph_pipeline.ainvoke({"event": event._data.model_dump()}, thread_id=session_id, context={"client": None, "tools": tool_registry.tools})` —— 入参只带 `event`，客户端由 `ON_TURN_START` 的 `build_client` 从根配置现建。
5. `ON_AGENT_START` 的 `event_adapter`（`ob11_adapter` 子插件，`priority=HIGH`）把 `state["event"]`（事件字典）交给解析链 → `event_data`，回填 `state["event"]`（供 `pick_tools` 读 `sender.user_id`），再序列化成 JSON 包成 `HumanMessage` **追加**进 `messages`；同事件的 `inject_account`（`account_injector` 子插件）把账号信息块写进 `prompts` 的 `account-info` 段（**`SectionPatch` 通道：按 key 打补丁，各插件写各自的段、互不覆盖**）；`ON_TURN_START` 先跑 `inject_soul` / `inject_output_protocol`（`miaoli_bot_adapter` 子插件，`priority=NORMAL+1`）写人格与输出协议，再由 `build_client`（`priority=NORMAL`）调 `miaoli_bot.api.build_client()` 从根配置建客户端写进 `runtime.context["client"]`（每轮现建，工具到 `on_request` 才绑）。
6. `ON_TURN_START` 之后进入**压缩三段**：`ON_BEFORE_COMPACT` 的守卫 `should_compact`（`context_compactor` 子插件，`priority=NORMAL`）算 token 判阈值 —— 不需要压缩就 `Goto(ON_BEFORE_REQUEST)` 直接往下走；需要压缩就 `Goto(ON_COMPACT)`，`compact` 节点把历史压成一条 `<abstract>` 摘要并返回 `{"messages": Overwrite([摘要, *保留窗口])}` 整体替换历史（`Overwrite` 是 langgraph 官方的「绕过 reducer 直接写入」包装，`merge_into_updates` 折叠多个处理器的产出时保留它、`merge_into_state` 构建视图时消费它，因此「整体替换」与其它处理器的「追加 / 定向删除」可以任意顺序组合），再由 `ON_AFTER_COMPACT` 的默认跳转**回到 `ON_TURN_START`** 重走一轮 —— 这一轮守卫会命中 `messages` 里的 `<abstract>` 标志并 `Abort`，本轮到此结束（`AgentAborted` 冒到 `ainvoke` 调用处，由 `main.py` 转成一条提示回复）。`ON_BEFORE_REQUEST` 批次（按 priority 降序）先跑 `build_prompt`（`priority=NORMAL+1`，`prompt_builder` 子插件）把 `prompts` 的各段拼成 `<key>value</key>` 并用 `Overwrite` 放到 `messages[0]`，再跑 `pick_tools`（`priority=1`）按 `config.yaml` 权限表与 `event.sender.user_id` 摘掉无权使用的工具（未声明的工具默认拒绝并打 warning）、随后 `ON_REQUEST` 先跑 `pending_tool_fixer`（`priority=NORMAL+2`）给悬空的 `tool_calls` 补上合成返回、`orphan_tool_fixer`（`priority=NORMAL+2`）删掉找不到发起者的 `ToolMessage`（两者只在上一轮异常中断留下坏形状时才有产出，历史本就合法时直接返回 `None`、不写任何增量），最后由 `call_llm` 直接把 `state["messages"]`（首条已是 `build_prompt` 放好的 `SystemMessage`）交给模型，返回的 `AIMessage` 追加进 `messages`。
7. `ON_AFTER_REQUEST` 由 `default_routing` 的 `on_after_request` 节点分流（它注册在最低优先级 `MINIMUM`，因此任何插件都能抢在它之前改道）：末条消息带 `tool_calls` → 跳 `ON_TOOL_CALLING`，由 `invoke_tools` 用 `ToolNode` 执行工具、`ToolMessage` 追加进 `messages`，若工具结果是**非字符串**内容（多模态块列表），由 `tool_attachment_fixer` 子插件把它整体挪成一条 `HumanMessage`（原 `ToolMessage` 正文换成 `replace_text`，只对 `models` 里声明的模型生效），然后跳回 `ON_TURN_START` 重走一轮（重跑 `build_client` / `pick_tools` / `call_llm`）；无 `tool_calls` → 跳 `ON_TURN_END`，再经 `on_turn_end` 跳 `ON_AGENT_END`，最后 `on_agent_end` 返回 `Goto(END)` 收尾（`END` 被 langgraph 过滤，于是没有下一跳）。
8. `ON_AGENT_END` 的 `latest_to_answer` 取 `messages[-1]`，是 `AIMessage` 就把 `content` 写进 `final_answer`（否则回退成携带 `thread_id` 的提示文案）。
9. `on_message` 拿 `final_state` 的 `final_answer`（用 `.get()` 兜底 —— 该键是 `UntrackedValue`，本轮没走到 `on_agent_end` 时不存在），按根配置 `split`（`enable` / `delimiter`）切块并跳过空块；若 `typing.enable`，每块按 `len(块) * uniform(base_speed ± speed_offset)` sleep；群聊的首块用 `event.reply`（带引用），其余块与私聊的全部块用 `utils.easier_send` 发回 QQ。
10. 插件卸载（`on_close`）：先 `await plugin_loader.unload_plugins()` 倒序卸载子插件（逐个 `deactivate()` 转发 `on_close()` + `unload()` 清 `sys.modules`；卸载失败的留在列表里，下次还能再试）—— **必须先于清共享容器**，子插件的 `on_close` 要靠 `HandlerRegistry` / `ToolRegistry` 把挂上去的节点和工具摘回去；再 `await self.cpa.close()` 显式关闭 checkpointer（sqlite 关 `aiosqlite` 连接、postgresql 关连接池、memory 无副作用）；最后显式 `drop` 掉已知键（含 `TOOL_REGISTRY` / `EVENT_PARSER` / `SEGMENT_PARSER` / `GRAPH_PIPELINE`），残留键只记 warning。

## 内置子插件

主包只保留 checkpointer 适配层、`HandlerRegistry` / `ToolRegistry` 两个注册器与 `core.Loader` 子插件加载框架（图管线在独立包 `miaoli_pipeline` 里），业务能力由子插件提供。以下十八个内置子插件位于本仓库的 `plugins/` 目录，`metadata.toml` 与配置模板 `config.example.yaml` 随仓库提交；各部署环境的真实 `config.yaml` 一律 gitignore（含根目录），部署时从模板复制一份再改：

| 子插件 | 提供 |
|---|---|
| `account_injector` | 账号注入：`inject_account` 在 `on_agent_start` 把管理员 / 机器人的 QQ 号与昵称拼成 `account-info` 段写进 `prompts` |
| `base_nodes` | 图节点：`build_client` / `call_llm` / `invoke_tools` / `latest_to_answer` / `output_checker`（`on_agent_end` 校验末条是 `AIMessage`）|
| `system_tools` | 系统工具：`bash` / `read_file` / `write` / `replace` / `read_image`（自带 `config.yaml` 与 `README.md`）。`read_image` 按 `support_image` 名单过滤格式 —— 这道过滤是**为了限制读取**（不做的话读什么都会被 b64 成图片塞进上下文，导致 400），**不是**给模型过滤不同类型的图片 |
| `default_routing` | 默认跳转（edgeless 拓扑的顺序来源）：**一个事件一个节点文件**，11 个节点各返回一条 `Goto`，把旧 `wire()` 的静态边与 `tools_condition` 条件边在插件层复原；`on_after_request` 按 `is_tool_calling(messages)` 分流工具循环与收尾；压缩三段也在这里兜底（`on_before_compact` 默认不压缩 → `ON_BEFORE_REQUEST`，`on_after_compact` 跳回 `ON_TURN_START`）。注册在最低优先级 `MINIMUM`，可被任何子插件抢跑 |
| `context_compactor` | 上下文压缩，拆成**守卫 + 压缩**两个节点：`should_compact` 挂 `on_before_compact`（`priority=NORMAL`）读模型真实 `context_window` / `max_tokens` 判阈值，返回 `Goto(ON_COMPACT)` 或 `Goto(ON_BEFORE_REQUEST)`；`compact` 挂 `on_compact`，把历史压成一条 `<abstract>` 摘要并用 `Overwrite` 整体替换。保留条数 / 提示词 / 是否回填系统提示词 / 计数方式全部配置化（`base` 粗估或 `tiktoken` 精确）；压缩提示词内置在 `utils/prompt_ops.py`（`compact.prompt_file` 可覆盖），守卫估算时把提示词一并计入；自带 `README.md` |
| `time_injector` | 时间注入：`inject_current_time` 每轮挂在 `on_turn_start`（`priority=NORMAL+1`）把当前时间写成 `prompts` 的 `current-time` 段，格式 `年-月-日-小时-分钟-秒` |
| `intent_recognition` | 意图识别：`recognize_intent` 挂 `on_before_request`（`priority=NORMAL+2`，必须早于 `prompt_builder` 的 `NORMAL+1` —— 数值大者先跑），按配置的 `matchers` 逐条匹配末条消息的正文 —— 一个 matcher 的多条 rule 是**「与」关系**（`all()`），命中就按 `encoding` 读 `file`，以 `name` 为键；全部命中项最后合成**一个** `intent-recognition` 段（`name` 只是段内子标签）。四种命中方式以 `mode` 为判别字段组成判别式联合：`single_keyword`（单关键字子串）/ `any_keywords`（任意一个命中）/ `min_keywords`（至少命中 `count` 个）/ `regex`（`re.search`）。多模态正文由 `get_content` 提取，只收带 `str` 型 `text` 键的字典块与裸字符串块，图片块 / `tool_use` 块跳过（避免 base64 data URL 进匹配文本）。单个 matcher 失败只失效自己并打 `ERROR` 日志；`enable` 默认 `false`。自带 `README.md` |
| `mcp_adapter` | MCP 适配：`recall_mcp_tools` 在 `on_before_request`（`priority=MEDIUM`）用 `MultiServerMCPClient` 拉取外部 MCP server 的工具，**按名去重**后合并进 `runtime.context["tools"]`；必须排在 `pick_tools`（`priority=1`）之前，否则 MCP 工具会绕过权限过滤。支持 `stdio` / `streamable_http` 两种传输，每个 server 可选 `reusable`（工具列表稳定则首次拉取后进缓存，由 `MCPClientRegistry` 管理）。自带 `README.md`。**未完成**：只做去重不做下架 |
| `meme_ops` | meme 工具：归档 / 发送 / 按 hash 删除；`inject_doc` 在 `on_agent_start`（`priority=NORMAL`）把 `plugins/meme_ops/data/meme_helper.md` 的内容写进 `prompts` 的 `meme-helper` 段，`inject_memes` 同事件把已归档表情包的 `hash: description: tags` 列表写进 `available-memes` 段，模型无需再调工具列举；`inject_doc` 给出归档前的四条判据；`enable: false` 时工具与节点都不注册；自带 `README.md` 说明隐私风险 —— 模型可能把用户发的普通图片误归档为表情包 |
| `miaoli_bot_adapter` | 人格与输出协议资产：两个节点都挂在 `on_turn_start`（`priority=NORMAL+1`），`inject_soul` / `inject_output_protocol` 用自己目录下的 `data/SOUL.md` 与 `data/output_protocol.md` 写出 `prompts` 的 `soul` / `output-protocol` 段 —— 主包不再持有任何提示词资产。`on_load` 还把根配置解析成 `PluginConfig` 放进 `SHARE_STORE`（`api.get_root_config()` 取）。自带 `config.example.yaml` 与 `README.md` |
| `orphan_tool_fixer` | 坏历史修复：`fix_orphan_tool_message` 在 `on_request`（`priority=NORMAL+2`）删掉找不到发起 `tool_calls` 的 `ToolMessage`（只产出定向删除增量） |
| `pending_tool_fixer` | 坏历史修复：`fix_pending_tool_call` 在 `on_request`（`priority=NORMAL+2`）给悬空的 `tool_calls` 补一条「工具未执行」的合成 `ToolMessage`（返回 `Overwrite` 整表替换） |
| `ob11_adapter` | OB11 事件适配（**纯 adapter，只解析不发送**）：`event_adapter` 在 `on_agent_start`（`priority=HIGH`）把 ncatbot 事件字典解析成 `event_data`，回填 `state["event"]` 并把 JSON 追加进 `messages`；两级解析链（`parsers/`）完全吃字典、不 import ncatbot 任何类。发送由 `main.py` 负责。自带 `config.yaml` 与 `README.md` |
| `prompt_builder` | 提示词拼装：`build_prompt` 在 `on_before_request`（`priority=NORMAL+1`）把 `state["prompts"]` 的各段拼成 `<key>value</key>`，用 `Overwrite` 放到 `messages[0]`；内容与现有首条 `SystemMessage` 相同时返回 `None` 不写增量。自带 `README.md` |
| `qq_platform_tools` | QQ 平台工具：发消息 / 发文件 / 下载文件 / 查消息 ID / 撤回消息 / 戳一戳（`send_poke`，`group_id` 有值为群内戳、无值为私聊戳）。自带 `README.md` |
| `tool_attachment_fixer` | 工具附件修复：`fix_tool_attachment` 在 `on_tool_call`（`priority=-2`）把非字符串的 `ToolMessage.content` 挪进紧跟其后的一条 `HumanMessage`（原 `ToolMessage` 正文换成 `replace_text`），让不接受 `tool` 消息带多模态块的模型不再 `400`；只对 `models` 里声明的模型生效（留空 = 全部），无改动时返回 `None`。自带 `README.md` |
| `tool_permission_manager` | 工具权限控制：按 `config.yaml` 的权限表（`admin` / `white_list` / `anyone` / `passerby` / `nobody` 五种），在 `on_before_request`（`priority=1`）把当前身份无权使用的工具从 `runtime.context["tools"]` 摘掉；未声明的工具默认拒绝并打 warning（`debug: false` 可关日志，不影响判定）。自带 `README.md` |
| `web_search` | 联网搜索：注册一个 `web_search` 工具（**工具名与后端无关**），`adapter` 选后端 —— `langsearch`（`POST /v1/web-search`）或 `deepseek`（`POST /v1/tools/search`），原始响应整体交给模型。`adapter` 只影响工具入参 schema 与返回数据形状，不影响工具名。自带 `README.md` |

> `orphan_tool_fixer` 与 `pending_tool_fixer` 成对：前者治「有返回没请求」，后者治「有请求没返回」。两者互不依赖、各自独立判断，谁先跑都不影响结果（`accumulate_data` 保证不同形态的增量可以任意顺序折叠）；触发场景是上一轮工具执行中途异常／并发冲突导致消息形状坏掉，此后每轮请求模型都会 `400 insufficient tool messages following tool_calls`。

子插件约定：目录下放 `metadata.toml`（`name` / `entry_class` / `description` / `dependences`；`entry_class` 是点号路径如 `main.IntentRecognition`，入口类在 `__init__.py` 里时只写类名）与入库的配置模板 `config.example.yaml`（真实 `config.yaml` 不入库）；**运行环境里必须有 `config.yaml`**，缺失时框架不会给 `{}`，`self.config` 就是 `None`（`PluginConfig.model_validate(None)` 直接 `ValidationError`，插件会在激活阶段被判失败）；入口类继承 `PluginProtocol`，在 `on_load` 里用 `HandlerRegistry` 挂图节点、`ToolRegistry` 注册工具（解析器由 `ob11_adapter` 自己的 `ParserRegistry` 管），在 `on_close` 里用 `HandlerRegistry.remove_*()` / `ToolRegistry.remove()` 把挂上去的节点与工具摘除，再释放其它资源。

## 安装与使用

1. **把本目录整体移动到 ncatbot 创建的 `plugins/` 目录下**（如 `/root/Ncatbot_QQ/plugins/miaoli_bot`）。这是 ncatbot 插件而不是 Python 包，**不走 pip 安装** —— ncatbot 启动时扫描 `plugins/`，见到 `manifest.toml` 就加载。
2. 确认运行环境已安装依赖（`manifest.toml` 的 `pip_dependencies` 会在 `plugin.auto_install_pip_deps` 打开时自动安装）：
   - `ncatbot5`（`>=5.5.8`，导入名 `ncatbot`）
   - `langgraph`（`>=1.2.12`）
   - `langchain-core`（`>=1.6.5`）：`@tool` 工具定义 / `BaseMessage` / `BaseChatModel` 等基础类型
   - `langchain-openai`（`>=1.6.6`）/ `langchain-deepseek`（`>=1.1.1`）/ `langchain-anthropic`（`>=1.0.0`）：三个客户端实现，按 `providers[].client` 选用
   - `langgraph-checkpoint-sqlite`（`>=3.1.1`，`database: sqlite` 时用到）
   - `langgraph-checkpoint-postgres`（`>=3.1.2`，`database: postgresql` 时用到）
   - `aiosqlite`（`>=0.22.1`）/ `psycopg`（`>=3.3.6`）/ `psycopg-pool`（`>=3.3.3`）：直接 import 的驱动与连接池（`SQLiteAdapter` / `PostgresqlAdapter` / `MemeSqlite`）
   - `aiofiles`（`>=24.1.0`）：`system_tools` 的 `write` / `replace` 工具异步写盘
   - `aiohttp`（`>=3.13.4`）：`web_search` 的 HTTP 客户端（`ClientSession`）
   - `pydantic`（`>=2.13.5`）：配置模型（`models/config/`）与各工具的参数 schema
   - `pyyaml`（`>=6.0.3`）：子插件 `config.yaml` 解析（`core/plugin/plugin.py` 的 `yaml.safe_load`）
   - `filetype`（`>=1.2.0`）
   - `pillow`（`>=12.3.0`）
   - `tiktoken`（`>=0.14.0`）
   - `langchain-mcp-adapters`（`>=0.3.2`）：`mcp_adapter` 的 `MultiServerMCPClient`（`langchain_mcp_adapters.client`）
   - `mcp`（`>=1.24.0`）：MCP 协议 SDK，由上面那个包带入，此处显式声明
   - **`miaoli_pipeline` 不在上面这一串里**：`pip_dependencies` 只接受「包名 + PEP 440 约束」，而它没上 PyPI，装不了。它是个普通 Python 包，得自己从**本地仓库目录**装一次 —— 见下方[依赖](#依赖)一节的注
3. 插件配置：`cp config.example.yaml config.yaml` 后填真实 `api_key`（`config.yaml` 含密钥、已 gitignore）。插件目录的 `config.yaml` 为默认值，全局 `config.yaml` 的 `plugin.plugin_configs.miaoli_bot` 同键覆盖；`on_load` 第一步即 `PluginConfig.model_validate(self.config)`，必填项缺失 / 路径不存在 / 类型不符都会抛 `ValidationError`，本插件加载失败并在日志留下 traceback（机器人其余部分不受影响）。

配置键名与 `models.PluginConfig` 的字段一一对应：

| 键 | 默认 / 必填 | 用途 |
|---|---|---|
| `provider` / `model` | **必填** | 要用哪个供应商、哪个模型 —— 两个名字，`model_validator` 会校验它们在 `providers` 里确实存在 |
| `providers` | **必填** | `List[Provider]`，至少一项；每项用 `name` 字段标识供应商名 |
| `providers[].name` | **必填** | 供应商名（`provider` 字段的取值） |
| `providers[].base_url` | **必填** | 请求地址（**不会拼路径**，填到 `/v1` 这一层） |
| `providers[].api_key` | **必填** | 鉴权密钥 |
| `providers[].client` | **必填** | 用哪家的客户端实现：`openai`（`ChatOpenAI`）/ `deepseek`（`ChatDeepSeek`，带 `reasoning_content`）/ `anthropic`（`ChatAnthropic`） |
| `providers[].models` | **必填** | `List[LLM]`，至少一项；每项用 `name` 字段标识模型名 |
| `providers[].models[].name` | **必填** | 模型名（`model` 字段的取值） |
| `providers[].models[].context_window` | `128000` | 上下文窗口 |
| `providers[].models[].max_tokens` | `4096` | 最大输出 |
| `providers[].models[].support_visions` | **必填** | 模型支持的模态输入，至少一项：`image` / `video` / `text` / `audio` |
| `account` | **必填** | `bot_id` / `admin_id` / `bot_nickname` / `admin_nickname`，四项全必填；`account_injector` 子插件的 `inject_account` 用它拼提示词块，`admin_id` 也是工具权限插件判定管理员的依据 |
| `split` | `SplitConfig()` | `enable`（默认 `true`）/ `delimiter`（默认 `null`，输出切块分隔符）—— `enable` 为真时 `delimiter` 必须非空，否则校验报错；`on_message` 用它把回复切块 |
| `typing` | `TypingConfig()` | `enable`（默认 `true`）/ `base_speed`（默认 `0`，每字打字秒数）/ `speed_offset`（默认 `0`，随机偏移）—— `on_message` 按 `len(块) * uniform(base_speed ± speed_offset)` sleep |
| `checkpointer` | `CheckPointerConfig()` | `database`（`memory` / `sqlite` / `postgresql`，默认 `memory`）/ `connect_to`（数据库地址，**非 `memory` 必填**）/ `extra`（额外参数，透传给适配器的 `connect(**kwargs)`；postgresql 认 `max_size` 默认 8 / `min_size` 默认 4 / `autocommit` 默认 `true` / `row_factory` 默认 `dict_row`）—— `on_load` 按 `database` 从 `CPA_MAPPING` 取适配器并 `connect`（**0.9.0 起已接线**），`on_close` 调 `close()` |
| `sub_plugin` | `SubPluginConfig()` | `enable`（默认 `false`，**当前未消费**）/ `load_from`（`List[DirectoryPath]`，默认空列表；目录不存在时 `PluginConfig.model_validate` 直接报 `path_not_directory`，不再拖到 `expand_paths()` 里才抛 `FileNotFoundError`）；`core.Loader` 依次 `prepare_plugins()`（读 `metadata.toml` + 过滤非包目录）→ `load_plugins()`（拓扑序逐个加载）→ `unload_plugins()` |

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
| `ncatbot5`（`>=5.5.8`，导入名 `ncatbot`） | QQ 机器人框架 / 事件与消息 API |
| `langgraph`（`>=1.2.12`） | 图管线（`StateGraph` / `Command` / `Overwrite` / `ToolNode` / checkpoint） |
| [`miaoli_pipeline`](https://github.com/lyt2011/miaoli_pipeline)（`>=1.1.0`） | 事件管线本体：`GraphPipeline`（`register_handler` / `unregister_handler` / `wire` / `compile` / `ainvoke` / 优先级编排）、`BaseNodeAction`（`Continue` / `Goto` / `Abort`）、`SectionPatch` 通道。**未发布到 PyPI**，只能从本地仓库目录安装，见下方注 |
| `langchain-openai`（`>=1.6.6`） | `ChatOpenAI`（`client: openai`，可指向任意 OpenAI 兼容端点） |
| `langchain-deepseek`（`>=1.1.1`） | `ChatDeepSeek`（`client: deepseek`）；三个实现里唯一会把 `reasoning_content` 放进 `additional_kwargs` 的那个 |
| `langchain-anthropic`（`>=1.0.0`） | `ChatAnthropic`（`client: anthropic`） |
| `langchain-core`（`>=1.6.5`） | `@tool` 工具定义、`BaseMessage` / `BaseChatModel` 等基础类型（主包与子插件都用） |
| `langgraph-checkpoint-sqlite`（`>=3.1.1`） | `AsyncSqliteSaver`（`checkpointer.database: sqlite`），带 `aiosqlite` / `sqlite-vec` |
| `langgraph-checkpoint-postgres`（`>=3.1.2`） | `AsyncPostgresSaver`（`checkpointer.database: postgresql`），带 `psycopg` / `psycopg-pool` |
| `aiosqlite`（`>=0.22.1`） | `SQLiteAdapter` 与 `meme_ops.MemeSqlite` 共用的异步 sqlite 驱动（连接分别由 `close()` / `__aexit__` 关） |
| `aiofiles`（`>=24.1.0`） | `system_tools` 的 `write` / `replace` 工具异步写盘（`aiofiles.open` + `async with`） |
| `aiohttp`（`>=3.13.4`） | `web_search` 的联网搜索请求（`ClientSession.post`）；它也是 `ncatbot5` 的传递依赖，此处显式声明 |
| `psycopg`（`>=3.3.6`）/ `psycopg-pool`（`>=3.3.3`） | `PostgresqlAdapter` 直接 import 的驱动与连接池（`AsyncConnectionPool`） |
| `pydantic`（`>=2.13.5`） | 配置模型（`BaseModel` / `Field` / `model_validator`）与工具参数 schema |
| `pyyaml`（`>=6.0.3`） | `core/plugin/plugin.py` 读子插件 `config.yaml` 的 `yaml.safe_load` |
| `filetype`（`>=1.2.0`） | `system_tools` 的图片类型嗅探（`read_image`） |
| `pillow`（`>=12.3.0`） | `context_compactor` 的图片宽高解析（`image_to_tokens`，据此估算图片 token） |
| `tiktoken`（`>=0.14.0`） | `context_compactor` 的精确 token 计数（`calculate.mode: tiktoken`） |
| `langchain-mcp-adapters`（`>=0.3.2`） | `mcp_adapter` 的 `MultiServerMCPClient`（拉取 / 调用外部 MCP server 的工具） |
| `mcp`（`>=1.24.0`） | MCP 协议 SDK（由 `langchain-mcp-adapters` 带入，此处显式声明以免上游依赖树变动时导入期 `ModuleNotFoundError`） |

> 注：以上依赖由 `manifest.toml` 的 `pip_dependencies` 声明 —— 但 **`miaoli_pipeline` 不在其中**：`pip_dependencies` 只接受「包名 + PEP 440 约束」，而 `miaoli_pipeline` **没有发布到 PyPI**，写包名装不上，写 git URL 又会自动安装失败。它是个能安装的普通 Python 包，只能从**本地仓库目录**装一次：
>
> ```bash
> pip install /path/to/miaoli_pipeline
> ```
>
> 装好后 `import miaoli_pipeline` 即可用；它的唯一依赖是 `langgraph>=1.2,<2`（已在上面声明）。
> 注：0.7.0 及以前依赖 `pi_bridge` 与外部 pi Agent 进程，0.8.0 起已整体移除。

## 项目状态

本节只描述**现在是什么样**，不随版本累积 —— 每一版改了什么见 [`CHANGELOG.md`](CHANGELOG.md)。

**已有形态**

- 主包只剩三件事：checkpointer 适配层、`HandlerRegistry` / `ToolRegistry` 两个注册器与 `core.Loader` 子插件加载框架。图管线本身已迁到独立包 [`miaoli_pipeline`](https://github.com/lyt2011/miaoli_pipeline)；它未上 PyPI，部署时从 GitHub 装
- 业务全部由 **18 个**子插件提供（见[内置子插件](#内置子插件)）。每个子插件自带 `README.md` 与入库的 `config.example.yaml`，真实 `config.yaml` 一律 gitignore，部署时从模板复制
- 端到端链路已在服务器上长时间运行：真实 QQ 消息 → OB11 事件字典 → 图管线 → LLM → 工具循环 → 回复
- 上下文压缩、工具权限、MCP 接入、联网搜索、表情包、意图识别都已接入，各自能独立开关（`enable`）
- LLM 客户端可在 `openai` / `deepseek` / `anthropic` 之间切换（`providers[].client`），统一由 `miaoli_bot.api.build_client()` 构建；`Provider` 只描述「连哪儿、用哪家的实现」，客户端实例由 `build_client` 节点每轮现建

**已知短板**

- **工具只有「谁能用」，没有「能干什么」**：进程以 root 身份运行，`tool_permission_manager` 管的是工具可见性；`bash` / `write` / `replace` 一旦放行，就没有文件系统边界
- **`mcp_adapter` 只做去重不做下架**：MCP server 撤掉的工具不会从工具表里消失
- **压缩摘要是「摘要的摘要」**：第二次压缩吃的是第一次压缩的产物，压缩次数一多细节必然流失，会话越长越明显
- **工具返回值不统一**：`system_tools` 的 `read_file` / `replace` / `write` / `read_image` 返回字符串，其余子插件的工具返回 `{"status": bool, ...}` 字典。模型侧要按工具名记忆两种格式，提示词里也没法笼统描述
- **`intent_recognition` 是纯字符串匹配**：没有语义理解，判据只拿到末条消息的正文。「上一轮是不是我发的」「这张图算不算表情包」这类需要上下文或工具返回的条件，当前的 `is_hit(data)` 签名装不下
