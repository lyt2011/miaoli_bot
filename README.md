# miaoli_bot

[English](README/en.md) | **简体中文**

- **版本**：0.48.3
- **定位**：一个基于 [Ncatbot](https://github.com/NapNeko/NcatBot) 的 QQ 机器人插件，用 **LangGraph** 自建图管线把通道收到的对话交给 LLM，让模型思考、回复并调用工具
- **入口**：`main.py`（插件类 `MiaoLiBot`）
- **运行载体**：Ncatbot 插件系统（NapCat/OneBot 协议）
- **LLM 客户端**：`llm.providers[].client` 选 `ChatOpenAI`（`langchain-openai`）/ `ChatDeepSeek`（`langchain-deepseek`）/ `ChatAnthropic`（`langchain-anthropic`），统一经 `miaoli_bot.api.build_client()` 构建
- **消息通道**：主包**不自挂** `@registrar.on_message`，只认「通道」这个抽象 —— QQ 事件入口与消息段解析由平级插件 `miaoli_qq_channel`（独立仓库）提供，主包用 `miaoli_bot.api.register_channel()` 把它的通道收进 `ChannelRegistry`
- **默认跳转**：edgeless 拓扑下「下一个事件是谁」由处理器主动声明，`default_routing` 子插件提供默认顺序（**一个事件一个节点文件**，每个只返回一条 `Goto`），并承担 `ON_AFTER_REQUEST` 的分支判断（末条有 `tool_calls` → 工具循环，否则 → 收尾）。它注册在**最低优先级** `MINIMUM`，任何子插件挂在任何更高档位都能抢在它之前改道或叫停

## 功能特性

- 🧩 **事件管线（edgeless 拓扑）**：`GraphPipeline` 在本仓库的 `core/graph_pipeline/` 里（泛型 `GraphPipeline[StateT, ContextT, InputT, OutputT]`，四个 TypeVar 取自 `langgraph.typing`）。事件名与注册门面在 `consts/graph_events.py` —— 8 个图事件常量集中在该文件，节点经 `HandlerRegistry.on(event, func, priority=0)` **显式**挂载（转发到 `GraphPipeline.register_handler`；同一事件可挂多个，按 `priority` 降序执行，`priority` 大者先跑；档位常量是 `consts/node_priorities.py` 的九档阶梯 `MAXIMUM`(9999) / `HIGHEST`(1000) / `HIGH`(100) / `MEDIUM`(10) / `NORMAL`(0) / `LOW`(-10) / `LOWEST`(-100) / `TRIVIAL`(-1000) / `MINIMUM`(-9999)）。`wire(GRAPH_EVENTS)` **不定义任何事件顺序**，只按声明顺序挂事件节点 + 一条入口边（`START → ON_AGENT_START`）；「下一个事件是谁」由处理器**主动返回跳转指令**决定：`return {...}` 累积增量并继续本事件剩余处理器、`Continue(updates=…)` 停止本事件剩余处理器、`Goto(goto=…, updates=…)` 跳到指定事件、`Abort(reason=…, updates=…)` 中止整轮图（`AgentAborted` 冒到 `ainvoke` 调用处）。**谁挂在哪个事件上、谁跳向哪里，都由子插件注册时声明**。
- 📡 **消息入口是通道**：主包不注册任何消息处理器，`on_message` 挂在平级插件 `miaoli_qq_channel` 上 —— 它把 QQ 事件记进环形缓冲，暴露成 `BaseChannel`（`name` + `platforms` + `drain()` + `reply(platform, thread_id, content)`）与 `BaseChannelMessage`（`thread_id` + `platform` + `to_content()`），再用 `api.register_channel()` 注册进主包的 `ChannelRegistry`。主包侧 `main.py` 由一个常驻 `tick` 任务负责唤醒 —— 它 `await` 在 `RUN_REQUESTED` 事件上、带 `tick.interval`（默认 60 秒）兜底超时；任何子插件 / 通道插件调 `api.please_run_graph()` 把事件 `set()` 就能提前唤醒（N 次请求合并成一次，醒来先消费再跑图）：`ChannelRegistry.to_surface()` 取一份只读快照，`batch_drain(atimeout=channel.atimeout)` 并发 `drain()` 各通道（单通道异常或超时只落在自己那一路），拿回 `{渠道实例: 渠道消息列表}` 的映射（一个通道一次交回它在缓冲里的全部会话，每个会话一项）；随后**串行**为每条消息跑图（每条一路 `graph.atimeout`），出结果就 `channel.reply(message.platform, message.thread_id, last.content)` —— `platform` 原路来原路回，不许把路由编码进 `thread_id` 的字符串前缀。
- 🔌 **子插件系统**：`core.Loader` 读 `sub_plugin.load_from`（`List[DirectoryPath]`，可给多个目录）下每个子目录的 `metadata.toml`，登记成 `PluginEntity`（缺元数据直接抛错、非包目录跳过），再按 `topology_sort_plugins()` 的依赖序逐个 `load()`：「注册成 Python 包 → 实例化 `entry_class` → 注入 `workspace` / `metadata` / `config` → `on_load()`」；单个插件失败只回滚 `unload()` 并标记 `erred`、打日志，依赖它失败的插件跳过。卸载走 `unload()`（清 `sys.modules` + 转发 `on_close`），按倒拓扑序执行。子插件用 `api.get_handler_registry().on(event, func, priority)` 挂图节点、`api.register_tool()` 注册工具 —— 两者都**返回一个注销函数**（`store_set` 同样返回），子插件把它收进 `self.undo_list`，`on_close` 里逐个调用即可摘干净（不摘就会在下一次加载时重复挂载）。
- 🧠 **LLM 接入**：`main.py` 只把 `message.to_content()` 包成一条 `HumanMessage` 送进图（纯文本通道返回字符串，多模态通道返回内容块列表；会话身份跟着消息走，主包不自己编）；`miaoli_bot_adapter` 子插件的 `inject_soul` / `inject_output_protocol` 节点（`ON_TURN_START`，`priority=MEDIUM`）分别读自己目录下的 `data/SOUL.md` 与 `data/output_protocol.md`，写进 `prompts` 的 `soul` / `output-protocol` 段，随后 `base_nodes` 的 `build_client` 节点（`ON_TURN_START`，`priority=NORMAL`）调 `api.build_client()` 从根配置直接建客户端（具体类由 `llm.providers[].client` 选）写进 `runtime.context["client"]`（**刻意不在建实例时绑工具** —— 工具表每轮都会变）；`call_llm` 节点用 `runtime.context["tool_surface"].tools`（`ToolRegistry.to_surface()` 的快照）`bind_tools` 后请求模型，并把 token 用量打进日志；工具循环由 `default_routing` 的 `on_after_request` 节点分流 —— 末条消息有 `tool_calls` 就跳 `ON_TOOL_CALLING` 执行工具、再回到 `ON_TURN_START` 重走一轮；没有就跳 `ON_TURN_END` 收尾。
- 🗜️ **上下文压缩（单节点 + 区间）**：`compact_if_need`（`base_nodes` 子插件，挂在 `ON_BEFORE_REQUEST`，`priority=HIGH`）先按模型真实 `context_window` / `max_tokens` 算门槛 —— `Σ base_calculate(message) < context_window - max_tokens` 就直接返回 `None`，不发请求；过了门槛再调 `get_compaction_range(messages)` 求出**待压缩的闭区间**，把这一段交给 `compact_now` 请求模型压成一条摘要，最后用 `Overwrite` 拼回 `[区间前原文, <summary> 摘要, 剪枝后的区间正文, 区间后原文]` 整体替换 `messages`。区间右端永远停在**最后一段连续用户原话之前**，因此群聊里用户连发的几十条 `HumanMessage` 无论后面挂的是工具轮还是普通回复都完整留在区间外；左端从最后一个 `SystemMessage` 之后开始，起点不落 `ToolMessage`、终点不回退到带 `tool_calls` 的 `AIMessage`，保证不拆工具组、不留孤儿工具结果。压缩器本体（`ChatHistory` / `TokenPruner` / `compact_now` / `base_calculate` / `extract_*` / `truncate_content_if_need`）与压缩提示词都在主包的 `core/compact/`，子插件只调用不持有。
- 📝 **提示词分段拼装**：`prompts` 不是一整个字符串，而是 `Dict[str, str]` —— 各子插件写各自的段（`{"identity": …}` / `{"style": …}`），写入 `None` 表示删除该段。`prompt_builder` 子插件的 `build_prompt` 节点（`ON_BEFORE_REQUEST`，`priority=NORMAL`）把全部段渲染成 `<key>` 换行 `value` 换行 `</key>`，按渲染后长度降序排序、用空行连接，再**滤掉已有的 `SystemMessage`** 后用 `Overwrite` 把拼好的系统提示放到 `messages[0]`；拼出来是空串、或与现有首条 `SystemMessage` 完全相同时返回 `None`，不白写一次 `Overwrite`。
- 📜 **状态与运行时分离**：`models.GraphState`（会话状态：`messages` 用 `add_messages` 进 checkpoint、`prompts` 用 `UntrackedSectionPatch` **不进 checkpoint**；不该落盘的东西一律放 `GraphRuntimeContext`）与 `models.GraphRuntimeContext`（不进 checkpoint 的运行时依赖：`tool_surface` 必填，`client` / `custom_status` / `custom_mapping` 可选）分离 —— `context` 不做浅拷贝、结果保持原引用，所以 LLM 客户端 / 锁这类不可序列化对象只能放 `context`（放 state 会因 msgpack 无法序列化而当场崩）。
- 🎛️ **配置模型化**：`PluginConfig` 含 `llm`（`LLMConfig`：`provider` / `model`（两个名字，由 `model_validator` 校验确实存在于 `providers` 里）/ `thinking_effort`（本项目的思考强度档位）/ `providers`（`List[Provider]`，每项用 `name` 字段标识 —— `Provider` 有 `name` / `base_url` / `api_key` / `client`（`openai` / `deepseek` / `anthropic`）/ `models`，而 `models` 是 `List[LLM]`、`LLM` 有 `name` / `context_window` / `max_tokens` / `support_visions` / `thinking_efforts`））、`tick`（`interval`，默认 60 秒）、`checkpointer`、`sub_plugin` 与 `graph`（`atimeout`，默认 60 秒，单条消息跑图的总超时）、`channel`（`atimeout`，默认 30 秒，拉取通道的超时）。
- 🛠️ **工具调用闭环**：工具统一经 `ToolRegistry` 注册、由 `ToolSurface` 给出本轮副本、由 `ToolNode` 执行。返回值目前**不统一**：`system_tools` 的读写工具返回纯字符串（失败时 `[..]` 包裹），meme / 联网 / MCP 工具仍是 `{"status": bool, ...}` 字典。主包不内置任何工具，系统 / meme / 联网搜索工具全部由内置子插件注册，外部 MCP server 的工具由 `mcp_adapter` 每轮追加；`tool_permission_manager` 子插件在 `ON_BEFORE_REQUEST` 按 `config.yaml` 的 `allow` / `refuse` 白名单摘工具（**未配置即摘除**，`debug` 只影响日志）。
- 🔍 **联网搜索**：`web_search` 子插件注册一个 `web_search` 工具（**工具名与后端无关**），`adapter` 选后端 —— 请求地址取自子插件 `config.yaml` 的 `api_url`（模板里 `langsearch` 为 `https://api.langsearch.com/v1/web-search`，另一个后端是 `deepseek`），原始响应整体交给模型。`adapter` 只影响工具的入参 schema 与返回数据形状，不影响工具名。实测**英文检索质量明显优于中文**（技术 / 包名类相关率约 65% vs 30%），工具 docstring 已要求模型优先用英文搜。另有一段 `web-search-helper` 提示词段（`ON_AGENT_START` 每轮写入 `prompts`），说明什么时候值得先查一次、`count` 该给多少、搜完之后怎么用。
- 🔧 **协议先行**：抽象集中在顶层 `protocols/`，不跟实现走 —— `plugin.py`（`PluginProtocol`：`on_load` / `on_close`）、`node_action.py`（`BaseNodeAction`，`Continue` / `Goto` / `Abort` 的共同基类）、`checkpointer_adapter.py`（`BaseCheckpointerSaverAdapter`）、`channel/`（`BaseChannel`：`name` / `platforms` / `drain` / `reply`；`BaseChannelMessage`：`thread_id` / `platform` / `to_content`）。子插件与各层都从这里取协议，不依赖具体实现。`platforms` 是通道自报的 `FrozenSet[str]`「我能收发哪些平台」，主包用它和每条消息自带的 `platform` 做**对称路由**：什么东西进来就什么东西出去
- 🗄️ **checkpointer 适配层**：`checkpointer.database` 在 `memory` / `sqlite` / `postgresql` 之间切换 checkpoint 存储 —— `core/checkpointer_adapters/` 的三个适配器把 `InMemorySaver` / `AsyncSqliteSaver` / `AsyncPostgresSaver` 收拢成同一门面（1:1 转发 `BaseCheckpointSaver` 的同步 / 异步协议方法，`connect(connect_to, **extra)` 建连、`close()` 释放），`main.py` 的 `CPA_MAPPING` 按 `database` 取类，`on_load` 注入图、`on_close` 统一关闭。
- 💾 **共享存储**：`core/share_store.py` 的 `SHARE_STORE` 是全局共享容器（`ShareStore` 的唯一实例）；core 的键在 `consts/share_store_keys.py`（`NCATBOT_API` / `RAW_CONFIG` / `PLUGIN_CONFIG` / `PLUGIN_DIR` / `GRAPH_PIPELINE` / `WORKSPACE_DIR` / `TOOL_REGISTRY` / `HANDLER_REGISTRY` / `INVOKE_LOCKS` / `CHANNEL_REGISTRY` / `MAIN_READY` / `RUN_REQUESTED`，共 12 个），子插件用自带命名空间键（如 `miaoli_bot_adapter` 的 `WORKSPACE`、`mcp_adapter` 的 `MCP_CLIENT_REGISTRY`）。子插件不直接操作它，一律走 `miaoli_bot.api`。`api.store_set()` 在键已存在时打一行 warning —— 这是为了揪「两个子插件撞键」；确实要按轮改写同一个键的调用方传 `overwrite=True`，就不会再报。
- 🚪 **`api/` 门面层**：子插件只从 `miaoli_bot.api` 取东西 —— 一个模块一类事：`channel_ops`（`register_channel`）、`config_ops`（`get_root_config`）、`llm_ops`（`build_client` / `get_model_info` / `get_provider_info`）、`platform_ops`（`get_ncatbot_api`）、`registry_ops`（`get_handler_registry`）、`store_ops`（`store_recall` / `store_set` / `store_contains`）、`sync_ops`（`get_invoke_lock` / `wait_main_ready` / `please_run_graph`）、`tool_ops`（`register_tool`），图执行 `safe_run_graph` 从 `core` 直接转出，发送封装 `easier_send` 从 `utils/sugar.py` 转出。`__all__` 共 16 项，「键名 + 取值路径 + 类型」这些内部细节锁在门面层里，子插件只依赖函数签名。
- 🧹 **导入分块与对齐**：模块顶部的导入按「`__future__` → 第三方 `from`（按顶层包名各成一块）→ 跨包自引用 `miaoli_bot.x` → 同包相对导入 `.` / `..` → 内置 `from` → 普通 `import`」排列，块与块之间空一行，块内按语句字符数从短到长；列对齐到组内最长前缀的下一个 4 的倍数（tab stop = 4），**换行导入是组尾** —— 它可以跟上面的行对齐，它下面的行另起一组。子插件只从主包的一层导入（`miaoli_bot.api` / `core` / `models` / `consts` / `protocols` / `utils`）。
- 🎭 **人格与输出协议外置**：主包不持有任何提示词资产 —— 人格（`plugins/miaoli_bot_adapter/data/SOUL.md`）与输出协议（`plugins/miaoli_bot_adapter/data/output_protocol.md`）都是 `miaoli_bot_adapter` 子插件的资产，由 `inject_soul` / `inject_output_protocol` 每轮读盘写进 `prompts` 的 `soul` / `output-protocol` 段；该子插件 `enable: false` 时这两个节点不注册。根 `data/` 只留 `intent_prompts/`（意图识别的本地私有文案，已 gitignore）。
- 🧪 **本地测试**：`tests/` 随仓库提交，根目录 `pytest.ini` 用 `pythonpath = ..` 把 `plugins/` 加进 `sys.path`、`testpaths = tests` 圈定用例目录、`asyncio_mode = auto` 让 `async def test_*` 不用加标记。当前覆盖 `models/config/` 的校验、`consts/node_priorities.py` 的档位、`SHARE_STORE`、`ToolRegistry` / `ToolSurface` 的注册与快照、`utils/` 的纯函数，其余待补。

## 架构设计

```
QQ / NapCat (OneBot 11)
        │ ncatbot 事件
        ▼
miaoli_qq_channel（平级插件，独立仓库）
        │  @registrar.on_message → 环形缓冲 → QQChannel / QQChannelMessage
        ▼  api.register_channel()
main.py  MiaoLiBot(NcatBotPlugin)      ← config.yaml → models.PluginConfig（llm / checkpointer / sub_plugin / channel）
        │   ① tick 任务：等 RUN_REQUESTED 事件，兜底 tick.interval（默认 60s）
        │   ② ChannelSurface.batch_drain(atimeout=channel.atimeout) 并发取空各通道，一个通道交回一批
        │   ③ 串行跑图（一条跑完再下一条，日志按会话成块）→ 跑完 channel.reply(...)
        ▼
miaoli_bot.core.GraphPipeline.ainvoke({"messages": [HumanMessage(to_content())]}, thread_id=<消息自带>, context=…)
        │
        │  START
        ▼
   ON_AGENT_START ── inject_mcp_tools（mcp_adapter，MEDIUM：MCP 工具追加进本轮工具表）
        │            helper_inject（time_injector，NORMAL：写 prompts 的 time-inject-helper 段）
        │            default_routing: on_agent_start → ON_TURN_START
        ▼
   ON_TURN_START ── inject_soul / inject_output_protocol（miaoli_bot_adapter，MEDIUM）
        │            recognize_intent（intent_recognition，NORMAL；默认 enable=false）
        │            build_client（base_nodes，NORMAL：根配置 → context["client"]）
        │            default_routing → ON_BEFORE_REQUEST
        ▼
   ON_BEFORE_REQUEST ── compact_if_need（base_nodes，HIGH：过门槛才压，Overwrite 拼回区间外原文）
        │               time_inject（time_injector，MEDIUM：按 interval 往 messages 末尾追加一条 <time-inject>）
        │               build_prompt（prompt_builder，NORMAL：prompts 各段 → messages[0]）
        │               pick_tools（tool_permission_manager，priority=LOW：按 allow / refuse 摘工具）
        ▼
   ON_REQUEST ── fix_pending_tool_call / fix_orphan_tool_message（MEDIUM：修坏消息形状）
        │        call_llm（base_nodes，NORMAL：bind_tools(tool_surface.tools) → 请求模型）
        ▼
   ON_AFTER_REQUEST ── default_routing: on_after_request（末条有 tool_calls？）
        │
        ├─ 有 tool_calls ──▶ ON_TOOL_CALLING ── invoke_tools（base_nodes，ToolNode → ToolMessage）
        │                                      └── 回到 ON_TURN_START（重走一轮）
        │
        └─ 无 tool_calls ──▶ ON_TURN_END ──▶ ON_AGENT_END
                                                ├── output_checker（base_nodes，LOWEST：校验末条是 AIMessage）
                                                └── on_agent_end → Goto(END)

        │  final_state["messages"] 的末条由 main.py 打进日志（回发通道尚未接线）
        ▼
```

### 目录结构

```
miaoli_bot/
├── main.py                        # 插件入口：MiaoLiBot（建容器 + 建图 + 起子插件加载器 + 定时唤醒）
├── manifest.toml                  # 插件清单（name / version / entry_class / pip_dependencies）
├── config.example.yaml            # 配置模板（config.yaml 已 gitignore，内含密钥不提交）
├── pytest.ini                     # pythonpath = .. / testpaths = tests / asyncio_mode = auto
├── __init__.py                    # 空文件，仅作包标记（分层靠各子包自己的 __init__）
├── api/                           # 子插件唯一入口（门面层，不直接暴露 SHARE_STORE）
│   ├── __init__.py                #   16 项门面导出（并额外转出 utils 的 easier_send）
│   ├── channel_ops.py             #   register_channel（注册通道并返回注销函数）
│   ├── config_ops.py              #   get_root_config（根配置对象）
│   ├── llm_ops.py                 #   build_client / get_model_info / get_provider_info
│   ├── platform_ops.py            #   get_ncatbot_api（框架运行时句柄）
│   ├── registry_ops.py            #   get_handler_registry（处理器注册器句柄）
│   ├── store_ops.py               #   store_recall / store_set / store_contains
│   ├── sync_ops.py                #   get_invoke_lock（执行锁）/ wait_main_ready（等主包就绪）
│   └── tool_ops.py                #   register_tool（注册工具并返回注销函数）
├── consts/                        # 常量集中定义
│   ├── graph_events.py            #   8 个图事件名 + GRAPH_EVENTS 声明顺序
│   ├── node_priorities.py         #   九档优先级阶梯（MAXIMUM 9999 … NORMAL 0 … MINIMUM -9999）
│   ├── id_prefix.py               #   会话键前缀（group- / private-）
│   └── share_store_keys.py        #   SHARE_STORE 键名（12 个）
├── core/                          # 框架层：图管线 / 压缩 / 加载 / 注册 / 共享容器 / 适配器
│   ├── __init__.py                #   对子插件转出的那一层（GraphPipeline / 三个注册器 / Loader …）
│   ├── share_store.py             #   SHARE_STORE：全局共享容器（ShareStore 唯一实例）
│   ├── graph_runner.py            #   safe_run_graph：套执行锁 + 异常兜底地跑图
│   ├── handler_registry.py        #   HandlerRegistry：event → 图节点注册（on(event, func, priority) 返回 disposer）
│   ├── compact/                   #   上下文压缩器（与图无关的纯能力层）
│   │   ├── compact_now.py         #     compact_now：区间正文 → 模型 → 摘要 + 剪枝结果
│   │   ├── chat_history.py        #     ChatHistory：messages → 带 [User] / [Assistant] 标签的行
│   │   ├── token_pruner.py        #     TokenPruner：按 retain_tokens 从尾部保留
│   │   ├── consts/                #     labels / prompt（COMPACT_PROMPT）/ tags
│   │   ├── runtimes/              #     CompactSuccess / CompactFailed
│   │   └── utils/                 #     base_calculate / extract_content / extract_tool_calls / truncate_content_if_need
│   ├── checkpointer_adapters/     #   in_memory_adapter / sqlite_adapter / postgresql_adapter（统一门面）
│   ├── graph_pipeline/            #   图管线本体
│   │   ├── graph_pipeline.py      #     GraphPipeline：register_handler / wire / compile / ainvoke
│   │   ├── actions/               #     Continue / Goto / Abort
│   │   ├── channels/              #     SectionPatch / UntrackedSectionPatch（按 key 打补丁，各插件写各自的段；后者不落盘）
│   │   └── runtimes/handler.py    #     处理器登记行（event + priority + func）
│   ├── notice_channel/            #   通道注册表 + 一轮内只读快照
│   │   ├── channel_registry.py    #     ChannelRegistry：register / unregister / to_surface
│   │   └── channel_surface.py     #     ChannelSurface：batch_drain（并发取空各通道未读）
│   ├── plugin/                    #   子插件加载框架
│   │   ├── loader.py              #     Loader：prepare_plugins / load_plugins / unload_plugins
│   │   ├── plugin.py              #     Plugin：from_path / load / unload（包构建 + 配置注入 + 实例化）
│   │   ├── plugin_entity.py       #     PluginEntity + Status（prepared / loaded / unloaded / erred）
│   │   ├── models/                #     PluginMetadata / Dependence / PluginTopologyRuntime
│   │   └── utils/                 #     topology_sort_plugins（拓扑排序）
│   │   ├── job.py                 #     Job：func + timer，launch / stop / schedule
│   │   └── timers/                #     Once / Every
│   └── tool/                      #   工具注册器
│       ├── registry.py            #     ToolRegistry：按名字存工具（register / unregister / to_surface）
│       └── surface.py             #     ToolSurface：一轮内使用的工具表副本（add / delete / tools）
├── data/
│   └── intent_prompts/            #   意图识别要注入的提示词（已 gitignore，本地私有文案，不入库）
├── errors/                        # 异常定义（10 个，各一文件一类）
│   ├── agent_aborted.py           #   AgentAborted（Abort 冒到 ainvoke 调用处）
│   ├── base_bot_error.py          #   BaseBotError 基类
│   ├── base_plugin_error.py       #   BasePluginError（子插件加载框架的异常基类）
│   ├── client_not_found.py        #   ClientNotFound（没有与该客户端对应的适配器）
│   ├── entry_class_not_found.py   #   EntryClassNotFound（元信息里的入口类找不到）
│   ├── metadata_missing_error.py  #   MetadataMissingError（缺 metadata.toml）
│   ├── model_not_found.py         #   ModelNotFound（供应商下没有声明的模型）
│   ├── not_a_package_error.py     #   NotAPackageError（插件目录不是合法包）
│   ├── provider_not_found.py      #   ProviderNotFound（供应商未在配置中声明）
│   └── repeat_dependence_error.py #   RepeatDependenceError（重复声明依赖）
├── models/                        # 数据模型
│   ├── graph_state.py             #   GraphState（messages 进 checkpoint / prompts 走不落盘通道）
│   ├── graph_runtime_context.py   #   GraphRuntimeContext（tool_surface 必填，client / custom_* 可选）
│   └── config/                    #   PluginConfig / LLMConfig / TickConfig / GraphConfig / Provider / LLM / ThinkingEffort / CheckpointerConfig / SubPluginConfig / ChannelConfig
├── plugins/                       # 13 个内置子插件（加载目录由 sub_plugin.load_from 指定）
├── protocols/                     # 抽象基类集中层（子插件依赖这里，不依赖具体实现）
│   ├── plugin.py                  #   PluginProtocol（on_load / on_close）
│   ├── node_action.py             #   BaseNodeAction（Continue / Goto / Abort 的共同基类）
│   ├── checkpointer_adapter.py    #   BaseCheckpointerSaverAdapter（connect / close）
│   └── channel/                   #   channel.py（BaseChannel：name / platforms / drain / reply）+ message.py（BaseChannelMessage：thread_id / platform / to_content，另导出 Content）
├── tests/                         # pytest 用例（test_config / test_node_priorities / test_store / test_tool_registry_family / test_utils__writing）
├── utils/                         # 工具函数
│   ├── config_ops.py              #   inject_workspace（把 $workspace 占位符替换成实际目录）
│   ├── pipeline_helper.py         #   增量折叠（merge_into_updates / merge_into_state …）
│   └── sugar.py                   #   easier_send（私聊 / 群聊发送）+ concatenate_id（会话键加前缀）
├── CHANGELOG.md                   # 版本索引
├── CHANGELOG/                     # 各版本完整记录（v<版本号>.md）
└── README.md / README/en.md       # 中文 / 英文说明
```

## 数据流

1. QQ 消息经 NapCat → ncatbot 分发给各插件：平级插件 `miaoli_qq_channel` 用 `@registrar.on_message()` 把每条私聊 / 群聊事件记进环形缓冲（最新在前，满载淘汰最旧），主包本身不注册任何消息处理器。
2. `main.py` 的 `tick` 任务负责唤醒：它 `await` 在 `RUN_REQUESTED` 事件上、带 `tick.interval`（默认 60 秒）兜底超时，事件被 `api.please_run_graph()` 置位就提前醒；醒来第一件事是把这个标志 `clear()`（消费式标记，清在跑图之前 —— 跑图期间到达的请求留到下一轮，不会被抹掉），再取 `TOOL_REGISTRY`，然后 `ChannelRegistry.to_surface()` 拿本轮快照、`batch_drain(atimeout=config.channel.atimeout)` 并发 `drain()` 各通道 —— 单个通道抛异常或超时只落在自己那一路，逐个打日志。
3. 拿回的是 `{渠道实例: 渠道消息列表}` 映射 —— 一个通道一次 `drain()` 交回它在缓冲里的**全部会话**，每个会话一项，项内是该会话本轮的全部事件（一个会话一条 = 一个回合）。`to_content()` 为空（空字符串或空列表；字符串再 `.strip()` 判长度）的消息在这一步直接丢掉，不会白跑一次图 —— 只带图片块的消息 `to_content()` 是块列表而不是空值，不会被误丢。
4. 每条消息**依次**跑一次 `safe_run_graph({"messages": [HumanMessage(content)]}, {"tool_surface": tool_registry.to_surface()}, thread_id=message.thread_id)` —— 入参只有一条 `HumanMessage`（`content` 是 `to_content()` 的原样返回，字符串或内容块列表），会话身份来自消息本身；客户端由 `ON_TURN_START` 的 `build_client` 从根配置现建；执行锁是 `INVOKE_LOCKS` 里**按 `thread_id`** 的那一把（同会话串行），在 `graph_runner.safe_run_graph` 里套住整次 `ainvoke`；本轮 tick 是一条跑完再下一条 —— 并发跑图会把日志搅成一坨，而框架的 formatter 只打 `message`、不带会话身份。
5. `ON_AGENT_START` 的 `inject_mcp_tools`（`mcp_adapter`，`priority=MEDIUM`）把外部 MCP server 的工具追加进本轮 `tool_surface`（同名工具直接顶替并打 warning），随后 `default_routing` 的 `on_agent_start` 跳 `ON_TURN_START`。
6. `ON_TURN_START` 先跑 `inject_soul` / `inject_output_protocol`（`miaoli_bot_adapter` 子插件，`priority=MEDIUM`）写人格与输出协议，`recognize_intent`（`intent_recognition`，`priority=NORMAL`）按配置的 workflow 匹配末条消息、命中就往 `messages` 追加一条 `<intent-recognition>` 的 `HumanMessage`（**不碰 `prompts`**，系统提示词每轮完全一致），再由 `build_client`（`priority=NORMAL`）调 `miaoli_bot.api.build_client()` 建客户端写进 `runtime.context["client"]`（每轮现建，工具到 `ON_REQUEST` 才绑），最后 `default_routing` 的 `on_turn_start` 跳 `ON_BEFORE_REQUEST`。
7. `ON_BEFORE_REQUEST` 打头的是 **`compact_if_need`（`base_nodes` 子插件，`priority=HIGH`，排在所有其它处理器之前）**：它用 `sum(base_calculate(message) for message in messages)` 估当前历史 token 数，小于 `context_window - max_tokens` 就返回 `None` 直接放行（不发任何请求）；过了门槛则调 `get_compaction_range(messages)` 求出一段闭区间 `[p_start, p_end]`，把这一段交给 `core.compact.compact_now()` 压成一条摘要，再用 `Overwrite([*messages[:p_start], HumanMessage(摘要), *剪枝后的区间正文, *messages[p_end + 1:]])` 整体替换历史（`Overwrite` 是 langgraph 官方的「绕过 reducer 直接写入」包装，`merge_into_updates` 折叠多个处理器的产出时保留它、`merge_into_state` 构建视图时消费它，因此「整体替换」与其它处理器的「追加 / 定向删除」可以任意顺序组合）。区间右端停在**最后一段连续 `HumanMessage` 的起点之前**，中间的分隔点既不落在 `ToolMessage` 上也不回退掉带 `tool_calls` 的 `AIMessage`，左端从最后一个 `SystemMessage` 之后起算 —— 所以系统提示词、当前这一轮的用户原话、以及任何半个工具轮都不会被送进压缩器。
8. 压缩之后 `ON_BEFORE_REQUEST` 批次接着跑（按 priority 降序）`time_inject`（`priority=MEDIUM`，`time_injector` 子插件）按 `interval` 节流追加时间戳，再跑 `build_prompt`（`priority=NORMAL`，`prompt_builder` 子插件）把 `prompts` 的各段拼成系统提示并用 `Overwrite` 放到 `messages[0]`，再跑 `pick_tools`（`priority=LOW`）按 `config.yaml` 的 `allow` / `refuse` 表把未放行的工具从 `runtime.context["tool_surface"]` 里摘掉（未声明的工具默认拒绝并打 warning）；随后 `ON_REQUEST` 先跑 `fix_pending_tool_call` / `fix_orphan_tool_message`（两者 `priority=MEDIUM`，只在上一轮异常中断留下坏形状时才有产出，历史本就合法时直接返回 `None`、不写任何增量），最后由 `call_llm`（`priority=NORMAL`）把 `state["messages"]`（首条已是 `build_prompt` 放好的 `SystemMessage`）交给模型，返回的 `AIMessage` 追加进 `messages`。
9. `ON_AFTER_REQUEST` 由 `default_routing` 的 `on_after_request` 节点分流（它注册在最低优先级 `MINIMUM`，因此任何插件都能抢在它之前改道）：末条消息带 `tool_calls` → 跳 `ON_TOOL_CALLING`，由 `invoke_tools`（`base_nodes`，`ToolNode`）执行工具、`ToolMessage` 追加进 `messages`，然后跳回 `ON_TURN_START` 重走一轮（重跑 `build_client` / `pick_tools` / `call_llm`）；无 `tool_calls` → 跳 `ON_TURN_END`，再经 `on_turn_end` 跳 `ON_AGENT_END`。
10. `ON_AGENT_END` 先跑 `output_checker`（`base_nodes`，`priority=LOWEST`）校验 `messages[-1]` 是 `AIMessage`，否则 `Abort`（空列表 / `ToolMessage` / `HumanMessage` / 未知类型四种理由）；最后 `on_agent_end` 返回 `Goto(END)` 收尾（`END` 被 langgraph 过滤，于是没有下一跳）。
11. 回发侧已经接到协议层：跑图返回 `{"messages": [...]}` 且末条是 `AIMessage` 时，`main.py` 调 `channel.reply(message.platform, message.thread_id, messages[-1].content)` —— 主包不碰 QQ，怎么发、要不要按空行切，都是渠道自己的事。
12. 插件卸载（`on_close`）：第一步 `clear()` 掉 `MAIN_READY`（宣告「不再运行」，`tick` 任务的完成回调据此保持静默、不重启）；紧接着 `cancel()` 那个任务并 `await` 它退出 —— **必须先停循环再卸插件**，否则它可能正拿着子插件的工具在跑图；然后 `await plugin_loader.unload_plugins()` 倒拓扑序卸载子插件（逐个清 `sys.modules` + `on_close()`；卸载失败的留待下次再试）—— **必须先于清共享容器**，子插件的 `on_close` 要靠 `HandlerRegistry` / `ToolRegistry` 把挂上去的节点和工具摘回去；接着 `await cpa.close()` 显式关闭 checkpointer（sqlite 关 `aiosqlite` 连接、postgresql 关连接池、memory 无副作用）；最后显式 `drop` 掉已知键（`TOOL_REGISTRY` / `HANDLER_REGISTRY` / `GRAPH_PIPELINE` / `CHANNEL_REGISTRY` / `INVOKE_LOCKS` / `RUN_REQUESTED` …），残留键只记 warning。

## 内置子插件

主包只保留图管线本体、checkpointer 适配层、`HandlerRegistry` / `ToolRegistry` / `ChannelRegistry` 三个注册器、`core.Loader` 子插件加载框架与最小调度器，业务能力由子插件提供。以下 13 个内置子插件位于本仓库的 `plugins/` 目录，`metadata.toml` 与配置模板 `config.example.yaml` 随仓库提交（`base_nodes` / `prompt_builder` 不读配置，故无模板）；各部署环境的真实 `config.yaml` 一律 gitignore（含根目录），部署时从模板复制一份再改。

> QQ 侧不在本目录 —— `miaoli_qq_channel` 是与 `miaoli_bot` **同级**的独立仓库（`plugins/miaoli_qq_channel/`），自己带两个子插件：`account_injector`（`inject_account` 挂 `on_agent_start`，把账号信息写进提示词）与 `qq_platform_tools`（5 个 QQ 平台工具：发消息 / 下载文件 / 查消息 / 撤回消息 / 戳一戳）。主包不认识 QQ，只通过 `BaseChannel` 与它对接。

| 子插件 | 提供 |
|---|---|
| `base_nodes` | 基础节点 保证图运作正常：`build_client`（`on_turn_start`，`NORMAL`）/ `compact_if_need`（`on_before_request`，`HIGH`）/ `call_llm`（`on_request`，`NORMAL`）/ `invoke_tools`（`on_tool_calling`，`NORMAL`）/ `output_checker`（`on_agent_end`，`LOWEST`）。`compact_if_need` 读模型真实 `context_window` / `max_tokens` 判门槛，过门槛才把 `get_compaction_range` 求出的区间交给 `core.compact.compact_now` 压缩并用 `Overwrite` 拼回；区间外的系统提示词、当前用户原话、工具组原样保留。自带 `README.md` |
| `default_routing` | 默认跳转（edgeless 拓扑的顺序来源）：**一个事件一个节点文件**，8 个节点各返回一条 `Goto`，把拓扑的默认顺序在插件层声明；`on_after_request` 按 `is_tool_calling(messages)` 分流工具循环与收尾。8 个节点全注册在 `MINIMUM`，可被任何子插件抢跑 |
| `intent_recognition` | 识别用户意图，据此注入本轮的提示内容：`recognize_intent` 挂 `on_turn_start`（`NORMAL`，比 `prompt_builder` 的 `on_before_request` 早一个阶段），按配置的 `workflows` 逐条匹配末条 AI / Human 消息的正文 —— 一个 workflow 的多条 rule 是**「与」关系**（`all()`），全部命中才把该 workflow 的文件内容以 `<name>` 标签拼成一条 `<intent-recognition>` 的 `HumanMessage` **追加进 `messages`**；四种命中方式以 `mode` 为判别字段组成判别式联合：`single_keyword`（单关键字子串）/ `any_keywords`（任意一个命中）/ `min_keywords`（至少命中 `count` 个）/ `regex`（`re.search`）。多模态正文由 `content_to_text` 只收 `text` 块与裸字符串，图片块等跳过（避免 base64 进匹配文本）。`enable` 默认 `false`。自带 `README.md` |
| `mcp_adapter` | MCP 适配 —— 接入 MCP server 并把其工具追加进本轮工具表：`inject_mcp_tools` 挂 `on_agent_start`（`MEDIUM`），用 `MultiServerMCPClient` 拉取工具后 `add` 进 `runtime.context["tool_surface"]`；必须排在 `pick_tools`（`ON_BEFORE_REQUEST`）之前，否则 MCP 工具会绕过权限过滤。支持 `stdio` / `streamable_http` 两种传输，`tool_prefix` 可给工具名加服务器名前缀，每个 server 可选 `reusable`（工具列表稳定则首次拉取后进缓存，由 `MCPClientRegistry` 管理）。自带 `README.md`。**未完成**：只做追加不做下架 |
| `meme_ops` | meme 素材库工具：归档 / 发送 / 按 hash 删除；`inject_doc` 挂 `on_agent_start`（`NORMAL`）把 `help_doc.path` 的内容写进 `prompts` 的 `meme-helper` 段，`inject_memes` 同事件把已归档表情包的 `hash: description: tags` 列表写进 `available-memes` 段，模型无需再调工具列举；`enable: false` 时工具与节点都不注册；自带 `README.md` 说明隐私风险 —— 模型可能把用户发的普通图片误归档为表情包 |
| `miaoli_bot_adapter` | 内部数据适配 + 人格资产：`on_load` 把原生配置 / `PluginConfig` / `workspace` 写进共享容器，`inject_soul` / `inject_output_protocol` 挂 `on_turn_start`（`MEDIUM`）用自己目录下的 `data/SOUL.md` 与 `data/output_protocol.md` 写出 `prompts` 的 `soul` / `output-protocol` 段；`enable: false` 时两个节点不注册。自带 `config.example.yaml` 与 `README.md` |
| `orphan_tool_fixer` | 修复孤儿工具返回 —— 「有返回没请求」：`fix_orphan_tool_message` 挂 `on_request`（`MEDIUM`），删掉找不到发起 `tool_calls` 的 `ToolMessage`，只产出定向删除增量（`RemoveMessage`），无孤儿时返回 `None` |
| `pending_tool_fixer` | 修复悬空工具调用 —— 「有请求没返回」：`fix_pending_tool_call` 挂 `on_request`（`MEDIUM`），给悬空的 `tool_calls` 补一条正文取自 `fix_message` 的合成 `ToolMessage`，返回 `Overwrite` 整表替换，无事可修时返回 `None` |
| `prompt_builder` | 把 state 里的提示词段拼成一条系统消息，插到消息列表最前面：`build_prompt` 挂 `on_before_request`（`NORMAL`），渲染 `<key>value</key>`、按长度降序、空行连接，滤掉已有 `SystemMessage` 后用 `Overwrite` 放到 `messages[0]`；空内容或与现有首条相同则返回 `None`。自带 `README.md` |
| `system_tools` | 系统工具：`bash` / `read_file` / `write` / `replace` / `read_image`（自带 `config.yaml` 与 `README.md`）。`read_image` 按 `support_image` 名单过滤格式 —— 这道过滤是**为了限制读取**（不做的话读什么都会被 b64 成图片塞进上下文，导致 400），**不是**给模型过滤不同类型的图片 |
| `time_injector` | 时间注入：`helper_inject` 挂 `on_agent_start`（`NORMAL`）把 `<time-inject>` 标签的读法写进 `prompts` 的 `time-inject-helper` 段；`time_inject` 挂 `on_before_request`（`MEDIUM`）按 `interval` 每会话节流，往 `messages` 末尾追加一条包在 `<time-inject>` 里的 `HumanMessage`（`%Y-%m-%d %H:%M %z` + ISO 星期，带时区偏移，不含秒）。时间值**刻意不进** `prompts` —— 它每轮都在变，进系统提示词会把前缀缓存整段撞碎；静态说明才进 `prompts`。`template` 可换外部模板文件（占位符 `$now` / `$weekday`；路径不存在时静默回落到内置模板），`config.yaml` 为**必需**（缺文件时 `model_validate(None)` 直接失败）。自带 `README.md` |
| `tool_permission_manager` | 工具权限控制：按 `config.yaml` 的 `allow` / `refuse` 表，在 `on_before_request`（`priority=LOW`）把未放行的工具从 `runtime.context["tool_surface"]` 里 `delete` 掉；未出现在表里的工具一律摘除（默认拒绝），`debug: true` 时对漏配的工具打 warning（只影响日志，不影响判定）。自带 `README.md` |
| `web_search` | 联网搜索工具：注册一个 `web_search` 工具（**工具名与后端无关**），`adapter` 选 `langsearch` 或 `deepseek`，请求地址与密钥取自 `config.yaml` 的 `api_url` / `api_key`（模板给的是 langsearch 的 `https://api.langsearch.com/v1/web-search`），原始响应整体交给模型；`adapter` 只影响工具入参 schema 与返回数据形状。另注册 `inject_helper`（`ON_AGENT_START`，`NORMAL`）把使用说明写进 `prompts` 的 `web-search-helper` 段（硬编码在 `consts/prompt.py`）。自带 `README.md` |

> `orphan_tool_fixer` 与 `pending_tool_fixer` 成对：前者治「有返回没请求」，后者治「有请求没返回」。两者互不依赖、各自独立判断，谁先跑都不影响结果（增量折叠对形态不敏感，定向删除与整表替换可以任意顺序组合）；触发场景是上一轮工具执行中途异常／并发冲突导致消息形状坏掉，此后每轮请求模型都会 `400 insufficient tool messages following tool_calls`。

子插件约定：目录下放 `metadata.toml`（`name` / `entry_class` / `description` / `dependences`；`entry_class` 是点号路径如 `main.IntentRecognition`，入口类在 `__init__.py` 里时只写类名）与入库的配置模板 `config.example.yaml`（真实 `config.yaml` 不入库）。加载器对**有** `config.yaml` 的插件做 `yaml.safe_load` 并把 `$workspace` 占位符替换成插件自身目录；缺 `config.yaml` 时 `self.config` 就是 `None`，此时若插件仍去 `PluginConfig.model_validate(self.config)` 就会 `ValidationError` 并在激活阶段被判失败。入口类继承 `PluginProtocol`，在 `on_load` 里用 `api.get_handler_registry().on(event, func, priority)` 挂图节点、`api.register_tool()` 注册工具、`api.store_set()` 写共享容器（都返回注销函数，收进 `self.undo_list`），在 `on_close` 里把 `undo_list` 逐个调用即可摘干净，再释放其它资源。

## 安装与使用

1. **把本目录整体移动到 ncatbot 创建的 `plugins/` 目录下**（如 `/root/Ncatbot_QQ/plugins/miaoli_bot`）。这是 ncatbot 插件而不是 Python 包，**不走 pip 安装** —— ncatbot 启动时扫描 `plugins/`，见到 `manifest.toml` 就加载。要让机器人真的收发 QQ 消息，还需要同级的 `miaoli_qq_channel` 插件。
2. 确认运行环境已安装依赖（`manifest.toml` 的 `pip_dependencies` 会在 `plugin.auto_install_pip_deps` 打开时自动安装）：
   - `ncatbot5`（`>=5.5.8`，导入名 `ncatbot`）
   - `langgraph`（`>=1.2.12`）
   - `langchain-core`（`>=1.6.5`）：`@tool` 工具定义 / `BaseMessage` / `BaseChatModel` 等基础类型
   - `langchain-openai`（`>=1.6.6`）/ `langchain-deepseek`（`>=1.1.1`）/ `langchain-anthropic`（`>=1.0.0`）：三个客户端实现，按 `llm.providers[].client` 选用
   - `langgraph-checkpoint-sqlite`（`>=3.1.1`，`database: sqlite` 时用到）
   - `langgraph-checkpoint-postgres`（`>=3.1.2`，`database: postgresql` 时用到）
   - `aiosqlite`（`>=0.22.1`）/ `psycopg`（`>=3.3.6`）/ `psycopg-pool`（`>=3.3.3`）：直接 import 的驱动与连接池（`SQLiteAdapter` / `PostgresqlAdapter` / `MemeSqlite`）
   - `aiofiles`（`>=24.1.0`）：`system_tools` 的 `write` / `replace` 工具异步写盘
   - `aiohttp`（`>=3.13.4`）：`web_search` 的 HTTP 客户端（`ClientSession`）
   - `pydantic`（`>=2.13.5`）：配置模型（`models/config/`）与各工具的参数 schema
   - `pyyaml`（`>=6.0.3`）：子插件 `config.yaml` 解析（`core/plugin/plugin.py` 的 `yaml.safe_load`）
   - `filetype`（`>=1.2.0`）
   - `langchain-mcp-adapters`（`>=0.3.2`）：`mcp_adapter` 的 `MultiServerMCPClient`（`langchain_mcp_adapters.client`）
   - `mcp`（`>=1.24.0`）：MCP 协议 SDK，由上面那个包带入，此处显式声明
3. 插件配置：`cp config.example.yaml config.yaml` 后填真实 `api_key`（`config.yaml` 含密钥、已 gitignore）。插件目录的 `config.yaml` 为默认值，全局 `config.yaml` 的 `plugin.plugin_configs.miaoli_bot` 同键覆盖；`on_load` 第一步即 `PluginConfig.model_validate(self.config)`，必填项缺失 / 路径不存在 / 类型不符都会抛 `ValidationError`，本插件加载失败并在日志留下 traceback（机器人其余部分不受影响）。

配置键名与 `models.PluginConfig` 的字段一一对应：

| 键 | 默认 / 必填 | 用途 |
|---|---|---|
| `llm` | **必填** | `LLMConfig`，模型侧的全部配置 —— 下面六行都是它的子键 |
| `llm.provider` / `llm.model` | **必填** | 要用哪个供应商、哪个模型 —— 两个名字，`model_validator` 会校验它们在 `llm.providers` 里确实存在 |
| `llm.thinking_effort` | **必填** | 本项目的思考强度档位，取值 `off` / `minimal` / `low` / `medium` / `high` / `xhigh` / `max` / `ultra`，且必须是被选模型 `thinking_efforts` 的某个键。**当前不消费**：`build_client()` 尚未把它传给客户端 |
| `llm.providers` | **必填** | `List[Provider]`，至少一项；每项用 `name` 字段标识供应商名 |
| `llm.providers[].name` | **必填** | 供应商名（`llm.provider` 字段的取值） |
| `llm.providers[].base_url` | **必填** | 请求地址（**不会拼路径**，填到 `/v1` 这一层） |
| `llm.providers[].api_key` | **必填** | 鉴权密钥 |
| `llm.providers[].client` | **必填** | 用哪家的客户端实现：`openai`（`ChatOpenAI`）/ `deepseek`（`ChatDeepSeek`，带 `reasoning_content`）/ `anthropic`（`ChatAnthropic`） |
| `llm.providers[].models` | `[]` | `List[LLM]`；每项用 `name` 字段标识模型名（`llm.provider` / `llm.model` 的校验会要求所选模型确实在这里） |
| `llm.providers[].models[].name` | **必填** | 模型名（`llm.model` 字段的取值） |
| `llm.providers[].models[].context_window` | **必填**（`>=65535`） | 上下文窗口 |
| `llm.providers[].models[].max_tokens` | **必填**（`>=2048`） | 最大输出 |
| `llm.providers[].models[].support_visions` | **必填** | 模型支持的模态输入，至少一项：`image` / `video` / `text` / `audio` |
| `llm.providers[].models[].thinking_efforts` | **必填** | `Dict[ThinkingEffort, str]`，至少一项。**「本项目档位 → 该供应商实际档位」的翻译表**：键只能取上面那八个合法档位，值是自由字符串（不同供应商喊法不同：DeepSeek 官方认 `minimal` / `low` / `medium` / `high` / `xhigh` / `max` / `ultra`，OpenAI 只认 `minimal` / `low` / `medium` / `high`）。**当前不消费**。注意 YAML 里 `off` 这种键必须加引号 —— YAML 1.1 会把裸的 `off` / `on` / `yes` / `no` 解析成布尔值 |
| `tick` | `TickConfig()` | `interval`（默认 `60.0`，必须 `> 0`）：`tick` 任务的兜底唤醒间隔（秒）。期间收到 `api.please_run_graph()` 会提前醒，间隔只是「没消息时最多等多久」|
| `checkpointer` | `CheckpointerConfig()` | `database`（`memory` / `sqlite` / `postgresql`，默认 `memory`）/ `connect_to`（数据库地址，**非 `memory` 必填**）/ `extra`（额外参数，透传给适配器的 `connect(**kwargs)`；postgresql 认 `max_size` 默认 8 / `min_size` 默认 4 / `autocommit` 默认 `true` / `row_factory` 默认 `dict_row`）—— `on_load` 按 `database` 从 `CPA_MAPPING` 取适配器并 `connect`，`on_close` 调 `close()` |
| `graph` | `GraphConfig()` | `atimeout`（默认 `60.0`）：单条消息跑图的总超时秒数 —— `tick` 给每条消息各套一路 |
| `channel` | `ChannelConfig()` | `atimeout`（默认 `30.0`）：`ChannelSurface.batch_drain` 对每个通道 `drain()` 的超时秒数 |
| `sub_plugin` | `SubPluginConfig()` | `enable`（默认 `false`，**当前未消费**）/ `load_from`（`List[DirectoryPath]`，默认空列表；目录不存在时 `PluginConfig.model_validate` 直接报 `path_not_directory`）；`core.Loader` 依次 `prepare_plugins()`（读 `metadata.toml` + 过滤非包目录）→ `load_plugins()`（拓扑序逐个加载）→ `unload_plugins()` |

4. 启动 bot。主包默认每 60 秒（`tick.interval`）从各通道取一次未读内容跑图（收到 `api.please_run_graph()` 会提前）；跑完把末条 `AIMessage` 交给 `channel.reply(platform, thread_id, content)`，真正的 QQ 回发要看渠道那边有没有实现 `reply`（见[项目状态](#项目状态)）。

### 本地测试

```bash
cd <插件父目录>          # plugins/
<venv>/bin/python -m pytest miaoli_bot/tests/ -v
```

> `pytest.ini` 在插件根目录：`pythonpath = ..` 负责把 `plugins/` 放进 `sys.path`，`testpaths = tests` 圈定用例目录，`asyncio_mode = auto` 负责让异步用例直接可跑。不需要在用例里写 `sys.path.insert`。

## 依赖

| 包 | 用途 |
|---|---|
| `ncatbot5`（`>=5.5.8`，导入名 `ncatbot`） | QQ 机器人框架 / 事件与消息 API |
| `langgraph`（`>=1.2.12`） | 图管线（`StateGraph` / `Command` / `Overwrite` / `ToolNode` / checkpoint） |
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
| `langchain-mcp-adapters`（`>=0.3.2`） | `mcp_adapter` 的 `MultiServerMCPClient`（拉取 / 调用外部 MCP server 的工具） |
| `mcp`（`>=1.24.0`） | MCP 协议 SDK（由 `langchain-mcp-adapters` 带入，此处显式声明以免上游依赖树变动时导入期 `ModuleNotFoundError`） |

> 注：早先版本依赖过 `pi_bridge` 与外部 pi Agent 进程，现在已整体移除，不再出现在依赖表里。

## 项目状态

本节只描述**现在是什么样**，不随版本累积 —— 每一版改了什么见 [`CHANGELOG.md`](CHANGELOG.md)。

**已有形态**

- 主包只剩几件事：图管线本体（`core/graph_pipeline/`）、checkpointer 适配层、`HandlerRegistry` / `ToolRegistry` / `ChannelRegistry` 三个注册器（后两者分别用 `ToolSurface` / `ChannelSurface` 给出每轮只读快照）、`core.Loader` 子插件加载框架。部署只需整目录同步，没有额外的本地包要装
- 业务全部由 **13 个**子插件提供（见[内置子插件](#内置子插件)）。每个子插件自带 `README.md`，读配置的还带入库的 `config.example.yaml`，真实 `config.yaml` 一律 gitignore，部署时从模板复制
- QQ 侧由**平级插件** `miaoli_qq_channel`（独立仓库）提供：事件入口、消息段解析、两个子插件（`account_injector` / `qq_platform_tools`）都在那边；主包只认 `BaseChannel` / `BaseChannelMessage`
- 链路形态是「事件唤醒 + 定时兜底 + 按会话跑图」：`tick` 任务被 `api.please_run_graph()` 提前唤醒、或每 `tick.interval`（默认 60 秒）兜底醒一次；每个渠道一次 `drain()` 交回全部会话各一条消息，**随后串行逐条跑图**（锁仍按 `thread_id` 分），跑完由 `channel.reply(message.platform, message.thread_id, last.content)` 回给该会话。上下文压缩、工具权限、MCP 接入、联网搜索、表情包、意图识别都已接入，各自能独立开关（`enable`）
- LLM 客户端可在 `openai` / `deepseek` / `anthropic` 之间切换（`llm.providers[].client`），统一由 `miaoli_bot.api.build_client()` 构建；`Provider` 只描述「连哪儿、用哪家的实现」，客户端实例由 `build_client` 节点每轮现建
- 消息进入图时是 `HumanMessage(message.to_content(), additional_kwargs={"platform": message.platform})` —— `to_content()` 是模型输入的**唯一**合同（字符串或 OpenAI 风格内容块列表），平台跟着 `additional_kwargs` 进图，出图时原路回到 `channel.reply(...)`。日志要用的纯文本由基类的 `__str__` 给（`<类名 平台:会话>`），**不调 `to_content()`** —— 多模态之后那是 base64

**已知短板**

- **通道侧还没交多模态**：`miaoli_qq_channel` 的 `to_content()` 仍是整包事件的 JSON 字符串，图片只以 NapCat 的 `url` / `file_id` 形式留在文本里，模型得自己调工具去取；要真正内联得先把图片转成 base64 内容块。主包这边已经通了（块列表原样进 `HumanMessage`，只带图片块的消息不会被当成空消息丢掉）
- **一轮 tick 串行跑图**：N 个会话的耗时会叠加，最坏要 `N × graph.atimeout` 才走完一轮；换来的是日志按会话成块、归属清楚。要提速就得并发 + 让框架日志带上会话身份（`formatter.py` 目前只打 `message`）
- **`\n\n` 的切分责任在渠道**：输出协议里「两个换行 = 对方收到两条独立 QQ 消息」，而 `reply` 只拿得到一个 `text`。主包不切，渠道想分条就得自己切
- **工具只有「谁能用」，没有「能干什么」**：进程以 root 身份运行，`tool_permission_manager` 管的是工具可见性（`allow` / `refuse` 白名单，未配置即摘除）；`bash` / `write` / `replace` 一旦放行，就没有文件系统边界
- **`mcp_adapter` 只加不删**：MCP server 撤掉的工具不会从工具表里消失；同名工具直接顶替并打 warning
- **区间小于保留量时压缩反而净增**：`compact_if_need` 的 `retain_tokens` 是 `20000` 的硬编码，`TokenPruner` 看区间正文不足这个数就一条都不删，而摘要照样插入 —— 区间本来就很小的场景（历史总量过门槛、但可压区间恰好很小）净效果是 `messages` 变长。实测 5,864 token 的区间会得到 +5.6% 的端到端 token 增长
- **门槛只看总量，不看区间**：触发条件由整段历史的 token 数决定，但真正被压的是 `get_compaction_range` 给出的区间，两者大小无关。区间超过 `context_window` 时压完仍可能超限，只能等下一轮再压
- **压缩摘要是「摘要的摘要」**：第二次压缩吃的是第一次压缩的产物，压缩次数一多细节必然流失，会话越长越明显
- **工具返回值不统一**：`system_tools` 的 `read_file` / `replace` / `write` / `read_image` 返回字符串，其余子插件的工具返回 `{"status": bool, ...}` 字典。模型侧要按工具名记忆两种格式，提示词里也没法笼统描述
- **`intent_recognition` 的注入可以自己喂自己**：`recognize_intent` 挂在 `ON_TURN_START`，判据是 `messages[-1]`，而注入产物本身也是 `HumanMessage`。这个事件有三条入边 —— `on_agent_start`（有新用户输入）、`on_tool_calling`（回流，没有新输入）。回流时末条可能正是刚注入的那条，或压缩后保留下来的那条，于是同一轮里会再命中、再注入；压缩又把注入消息留在尾部，两者互相喂，只受 langgraph 递归上限打断。工具执行失败（`_dispatch` 吞掉异常、没有 `ToolMessage` 产出）时则是每轮多一条，永久留在 checkpoint 里
- **`intent_recognition` 是纯字符串匹配**：没有语义理解，判据只有末条消息的正文。「上一轮是不是我发的」「这张图算不算表情包」这类需要上下文或工具返回的条件，当前的 `is_hit(content)` 签名装不下
