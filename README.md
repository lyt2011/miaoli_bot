# miaoli_bot

一个基于 [Ncatbot](https://github.com/NapNeko/NcatBot) 的 QQ 机器人插件，用 **LangGraph** 自建图管线把 QQ 对话接给 LLM，让 QQ 消息驱动模型思考、回复并调用工具。

- **版本**：0.9.4
- **入口**：`main.py`（插件类 `MiaoLiBot`）
- **运行载体**：Ncatbot 插件系统（NapCat/OneBot 协议）
- **LLM 客户端**：`langchain-openai` 的 `ChatOpenAI`（`base_url` 指向任意 OpenAI 兼容端点）
- **阶段**：插件化拆分完成，当前处于**优化态** —— 主包只剩图管线、checkpointer 适配层与子插件加载框架，业务由子插件提供，后续以补齐错误处理与体验优化为主

## 功能特性

- 🧩 **自建图管线**：`core.GraphPipeline`（泛型 `GraphPipeline[StateT, ContextT, InputT, OutputT]`，四个 TypeVar 取自 `langgraph.typing`）把「事件 → 处理器」的编排抽成独立类 —— 8 个图事件常量集中在 `consts/graph.py`，节点用 `register(event, node, priority=0)` **显式**挂载（同一事件可挂多个，按 `priority` 排序），`wire()` 一次性产出 8 节点 + 8 条边，`compile(checkpointer=…)` 出 `CompiledStateGraph`。**谁挂在哪个事件上，由子插件注册时声明**。
- 🔌 **子插件系统**：`core.PluginLoader` 扫描 `sub_plugin.load_from` 下带 `plugin.toml` 的子目录，把每个子目录注册成 Python 包后实例化入口类并调 `on_load()`；子插件通过 `core.Registry` 注册工具 / 解析器 / 图节点；卸载时 `on_close()` 并把整包从 `sys.modules` 抹掉，改完代码重载立即生效。
- 🧠 **LLM 接入**：`ChatOpenAI` 经 `models.GraphRuntimeContext` 的 `chat_model` 注入图；`call_llm` 节点用 `runtime.context["tools"]`（来自 `ToolRegistry`）`bind_tools` 后请求模型；工具循环由 `tools_condition` 条件边在「有 `tool_calls` → 执行工具 → 回到请求」与「无 `tool_calls` → 收尾」之间自动分流。
- 📜 **状态与运行时分离**：`models.GraphState`（进 checkpoint 的会话状态：`event` / `segments` / `messages` / `final_answer` / `system_prompt`）与 `models.GraphRuntimeContext`（不进 checkpoint 的运行时依赖：`plugin_config` / `chat_model` / `tools`）分离 —— `context` 不做浅拷贝、结果保持原引用，所以 LLM 客户端 / 锁这类不可序列化对象只能放 `context`。
- 🎛️ **配置模型化（分层 + 更名）**：`PluginConfig` 含 `providers`（`Provider(name / base_url / api_key / models: [LLM(name / context_window / max_tokens / visions / protocol)])`）、`account`（`bot_id` / `root_id` / `bot_nickname` / `root_nickname`，四项全必填）、`output`、`checkpointer`、`sub_plugin` 与 `session_dir` / `prompt_file` / `system_prompt`；`DirectoryPath` / `FilePath` 让路径在**加载期**就被校验，缺失即 `ValidationError`。
- 🛠️ **工具调用闭环**：工具统一经 `ToolRegistry` 注册、由 `ToolNode` 执行，返回值经 `utils.tool_result_builder` 的 `success` / `fail` / `custom` 收敛成 `{"status": bool, "message": …}`；主包不再内置任何工具，平台 / 系统 / meme 工具全部由内置子插件注册。
- 🧩 **两级解析链**：`EventParseChain`（群 / 私聊事件元数据）与 `SegmentParseChain`（文本 / AT / 图片 / 文件 / 引用消息段）双链分发，`utils.easier_parser.parse_message` 一步合并产出 `ParseResult(event, segments)` 喂给图；解析器由 `base_parsers` 子插件注册。
- 🖼️ **多类型消息段**：`Text` → `{text}`、`At` → `{at}`、`Image` → `{image, size, is_meme}`（`QQImageSegmentParser` 只接受 QQ 平台侧 `ncatbot.types.qq.QQImage`，`is_meme` 即其 `sub_type` 非 0）、`File` → `{file, size}`、`Reply` → `{reply}`。
- 🦆 **鸭子类型适配**：`adapters/EventAdapter` 不依赖具体 ncatbot 类型，通过属性探测兼容不同消息事件形态（`user_id` / `group_id` / `is_group` / `send`）；`utils.get_id_from_event` 群取 `group_id`、私聊取 `user_id`。
- 🔧 **协议先行**：`protocols/abc/` 定义编译期抽象（`PluginProtocol` / `ChainProtocol` / `StoreProtocol` / `BaseCheckpointerSaverAdapter`），`protocols/runtime/` 定义运行时检查协议（`Parser`，带 `@runtime_checkable`，可 `isinstance` 判定）。
- 🗄️ **checkpointer 适配层**：`checkpointer.database` 在 `memory` / `sqlite` / `postgresql` 之间切换 checkpoint 存储 —— `adapters/check_pointers/` 的三个适配器把 `InMemorySaver` / `AsyncSqliteSaver` / `AsyncPostgresSaver` 收拢成同一门面（`protocols.BaseCheckpointerSaverAdapter`：1:1 转发 `BaseCheckpointSaver` 的同步 / 异步协议方法，`connect(connect_to, **extra)` 建连、`close()` 释放），`main.py` 的 `CPA_MAPPING` 按 `database` 取类，`on_load` 注入图、`on_close` 统一关闭。
- 💾 **共享存储**：`stores/SHARE_STORE` 全局共享容器，键集中定义于 `consts/share_store_keys.py`（`EVENT_PARSER` / `SEGMENT_PARSER` / `TOOL_REGISTRY` / `NCATBOT_API` / `PLUGIN_CONFIG` / `RAW_CONFIG` / `PLUGIN_DIR` / `WORKSPACE_DIR` / `GRAPH_PIPELINE`）。
- 🔔 **事件优先级让位**：`on_message` 以 `priority=-100` 注册，排在后处理的位置 —— 扩展插件可用更高优先级抢先接收并停止事件传播（如 `miaoli_like` 的 `赞我` 用 `priority=100`），被上游截下的消息不会再进入 LLM。
- 🎭 **角色扮演**：内置猫娘「喵璃」人设提示词（`data/prompts/prompt_v1.3.md`，另有 v1.0 ~ v1.2 历史版本）；`format_prompt` 节点把人设与管理员 / 机器人的 QQ 号、昵称拼成 `<account>` 标签块，一起写进系统提示词。
- ⏱️ **输出切块与打字延迟**：按 `output.split_separator` 把回复切块（跳过空块），每块按 `len(块) * typing_speed ± typing_speed_offset` 随机 sleep 后再发送，模拟真人在打字。
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
        ▼
   ON_TURN_START
        ▼
   ON_BEFORE_REQUEST ── format_prompt（<account> 信息块 + 人设 → system_prompt 键）
        ▼
   ON_REQUEST ── compact（超窗压缩）→ call_llm ──▶ bind_tools(tools) → ChatOpenAI
        │                                              │
        │                                              ▼
   ON_AFTER_REQUEST                           AIMessage（含 tool_calls）
        │
        │  tools_condition   ├── 有 tool_calls ──▶ ON_TOOL_CALLING ── invoke_tools → ToolMessage
        │                    │                     （attach_image 把图片挪进 HumanMessage）
        │                    │                     （回到 ON_BEFORE_REQUEST）
        └────────────────────┴── 无 tool_calls ──▶ ON_TURN_END
                                                        ▼
                                                   ON_AGENT_END ── latest_to_answer（messages[-1] → final_answer）
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
│   ├── graph.py                   #   8 个图事件名（ON_TURN_START 等）+ MAX_PRIORITY / MIN_PRIORITY
│   ├── id_prefix.py               #   会话键前缀（group- / private-）
│   └── share_store_keys.py        #   SHARE_STORE 键名（含 TOOL_REGISTRY）
├── core/                          # 图管线与子插件加载
│   ├── graph_pipeline.py          #   GraphPipeline：register / wire / compile / ainvoke / _dispatch / _merge
│   ├── plugin_loader.py           #   PluginLoader：扫 plugin.toml → 注册成包 → 加载 / 卸载子插件
│   ├── registry.py                #   Registry：子插件的注册门面（工具 / 解析器 / 图节点），含全局单例 registry
│   └── tool_registry.py           #   ToolRegistry：按名字存工具（register / remove / tools）
├── data/prompts/                  # 提示词资产（prompt_v1.0.md ~ prompt_v1.3.md）
├── errors/                        # 异常定义
│   ├── base_bot_error.py          #   BaseBotError 基类
│   ├── api_unavailable_error.py   #   APIUnavailableError（工具里 api 不可用时抛）
│   └── session_manager_closing_error.py # SessionManagerClosingError
├── models/                        # 数据模型
│   ├── config/                    #   PluginConfig / Provider / LLM / Accounts / OutputConfig / SubPluginConfig / CheckPointerConfig
│   ├── graph_state.py             #   GraphState（进 checkpoint：event / segments / messages / final_answer / system_prompt）
│   ├── graph_runtime_context.py   #   GraphRuntimeContext（不进 checkpoint：plugin_config / chat_model / tools）
│   └── runtime/                   #   Handler（图处理器登记单元）/ ParseResult / DispatchResult
├── plugins/                       # 内置子插件（随仓库提交，加载目录由 sub_plugin.load_from 指定）
│   ├── base_nodes/                #   图节点（nodes/ + plugin.toml）
│   ├── base_parsers/              #   两级解析器（event_parsers/ + segment_parsers/）
│   ├── base_platform_tools/       #   平台工具（file_ops/ + message_ops/）
│   ├── base_system_tools/         #   系统工具（tools/ + models/ + consts/ + config.yaml 默认值）
│   └── meme_extension/            #   meme 工具（tools/ + core/ + models/ + consts/ + config.yaml 默认值 + README）
├── protocols/                     # 抽象协议
│   ├── abc/                       #   编译期抽象：PluginProtocol / ChainProtocol / StoreProtocol / BaseCheckpointerSaverAdapter
│   └── runtime/                   #   运行时检查：Parser（@runtime_checkable）
├── stores/                        # 全局共享存储（SHARE_STORE）
├── tests/                         # 本地 pytest 用例（gitignore，不提交；当前待重写）
└── utils/                         # 工具函数
    ├── easier_parser.py           #   parse_event / parse_segment / parse_message 快捷入口
    ├── easier_sender.py           #   private / group 便捷发送封装
    ├── event_ops.py               #   get_id_from_event（群 → group_id，私聊 → user_id）
    ├── sugar.py                   #   concatenate_id（会话键加 group- / private- 前缀）
    └── tool_result_builder.py     #   custom / success / fail（工具返回值统一契约）
```

## 数据流

1. QQ 消息经 NapCat → ncatbot → 按注册优先级分发给各插件：本插件以 `priority=-100` 排在后处理位置，上游插件若停下事件传播（如 `miaoli_like` 的 `赞我` 用 `priority=100`）本插件就收不到；群聊消息还必须 @ 到 `plugin_cfg.account.bot_id`。
2. `on_message` 先建 `EventAdapter` 与 `session_id`，再调 `parse_message(event, message)`（内部走 `EventParseChain` / `SegmentParseChain`，解析器由 `base_parsers` 子插件注册）→ `ParseResult(event, segments)`。
3. `session_id = concatenate_id(target_id, is_group=is_group)`（群 → `group-<group_id>`，私聊 → `private-<user_id>`），作为 LangGraph 的 `thread_id` —— 同一会话共享同一个 checkpointer（由 `checkpointer.database` 选中的 memory / sqlite / postgresql 实现）里的 checkpoint，跨轮记忆不串台。
4. `graph_pipeline.ainvoke({"event": …, "segments": …}, thread_id=session_id, context={"plugin_config": …, "chat_model": …, "tools": tool_registry.tools})`。
5. `ON_AGENT_START` 的 `format_input` 把 `event` + `segments` 序列化成 JSON 文本包成 `HumanMessage` **追加**进 `messages`；`ON_BEFORE_REQUEST` 的 `format_prompt` 把 `<account>` 信息块 + 人设写进 `system_prompt` 键（普通键，每轮覆盖而不是追加，否则每轮多留一份人设）。
6. `ON_REQUEST` 先跑 `compact`（`priority=-10`：token 超窗时把历史压成一条 `<compaction>` 摘要，`RemoveMessage(REMOVE_ALL_MESSAGES)` 清空后放回摘要与保留窗口），再由 `call_llm` 以 `[SystemMessage(state["system_prompt"]), *state["messages"]]` 请求模型，返回的 `AIMessage` 追加进 `messages`。
7. `ON_AFTER_REQUEST` 由 `tools_condition` 分流：有 `tool_calls` → `ON_TOOL_CALLING` 的 `invoke_tools` 用 `ToolNode` 执行工具、`ToolMessage` 追加进 `messages`（若工具结果带图片，`attach_image` 会把图片块挪成一条 `HumanMessage`），回到 `ON_BEFORE_REQUEST` 再请求一次；无 `tool_calls` → `ON_TURN_END`。
8. `ON_TURN_END` 无节点；`ON_AGENT_END` 的 `latest_to_answer` 取 `messages[-1]`，是 `AIMessage` 就把 `content` 写进 `final_answer`（否则回退成固定文案）。
9. `on_message` 拿 `output["final_answer"]`，按 `output.split_separator` 切块并跳过空块，每块按 `len(块) * typing_speed ± typing_speed_offset` 随机 sleep 后交给 `EventAdapter.send(self.api, …)` 发回 QQ。
10. 插件卸载（`on_close`）：先显式 `drop` 掉已知键（含 `TOOL_REGISTRY` / `EVENT_PARSER` / `SEGMENT_PARSER` / `GRAPH_PIPELINE`），再 `plugin_loader.unload_all()` 卸载子插件（逐个 `on_close()` 并从 `sys.modules` 抹掉整包），最后 `await self.cpa.close()` 显式关闭 checkpointer（sqlite 关 `aiosqlite` 连接、postgresql 关连接池、memory 无副作用），残留键只记 warning。

## 内置子插件

主包只保留图管线与加载框架，业务能力由子插件提供。以下五个内置子插件位于本仓库的 `plugins/` 目录，`plugin.toml` 与子插件自带的 `config.yaml` 默认值都随仓库提交（根目录的 `config.yaml` 仍 gitignore，不进版本控制）：

| 子插件 | 提供 |
|---|---|
| `base_nodes` | 图节点：`format_input` / `format_prompt` / `compact` / `call_llm` / `invoke_tools` / `attach_image` / `latest_to_answer`；含上下文压缩与图片附加 |
| `base_parsers` | 两级解析器：群 / 私聊事件 + 文本 / AT / 图片 / 文件 / 引用消息段 |
| `base_platform_tools` | 平台工具：发消息 / 发文件 / 下载文件 / 查消息 ID / 撤回消息 |
| `base_system_tools` | 系统工具：`bash` / `read_file` / `write` / `replace` / `read_image`（自带 `config.yaml`） |
| `meme_extension` | meme 工具：归档 / 发送 / 列举 / 按标签搜索 / 按 hash 删除（自带 `config.yaml`）；自带 `README.md` 说明隐私风险 —— 模型可能把用户发的普通图片误归档为表情包 |

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
   - `pydantic`（`>=2.13.5`）：配置模型（`models/config/`）与各工具的参数 schema
   - `pyyaml`（`>=6.0.3`）：子插件 `config.yaml` 解析（`core/plugin_loader.py` 的 `yaml.safe_load`）
   - `filetype`（`>=1.2.0`）
3. 插件配置：`cp config.example.yaml config.yaml` 后填真实 `api_key`（`config.yaml` 含密钥、已 gitignore）。插件目录的 `config.yaml` 为默认值，全局 `config.yaml` 的 `plugin.plugin_configs.miaoli_bot` 同键覆盖；`on_load` 第一步即 `PluginConfig.model_validate(self.config)`，必填项缺失 / 路径不存在 / 类型不符都会抛 `ValidationError`，本插件加载失败并在日志留下 traceback（机器人其余部分不受影响）。

配置键名与 `models.PluginConfig` 的字段一一对应：

| 键 | 默认 / 必填 | 用途 |
|---|---|---|
| `providers` | `[]` | 供应商列表，每项 `Provider(name / base_url / api_key / models)` |
| `providers[].base_url` | **必填** | 请求地址（**不会拼路径**，填到 `/v1` 这一层） |
| `providers[].api_key` | **必填** | 鉴权密钥 |
| `providers[].models` | `[]` | 模型列表，每项 `LLM(name / context_window / max_tokens)` |
| `account` | **必填** | `bot_id` / `root_id` / `bot_nickname` / `root_nickname`，四项全必填；`format_prompt` 用它拼 `<account>` 提示词块 |
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
| `langgraph`（`>=1.2.12`） | 图管线（`StateGraph` / `ToolNode` / `tools_condition` / checkpoint） |
| `langchain-openai`（`>=1.6.6`） | `ChatOpenAI`（可指向任意 OpenAI 兼容端点） |
| `langchain-core`（`>=1.6.5`） | `@tool` 工具定义、`BaseMessage` / `BaseChatModel` 等基础类型（主包与子插件都用） |
| `langgraph-checkpoint-sqlite`（`>=3.1.1`） | `AsyncSqliteSaver`（`checkpointer.database: sqlite`），带 `aiosqlite` / `sqlite-vec` |
| `langgraph-checkpoint-postgres`（`>=3.1.2`） | `AsyncPostgresSaver`（`checkpointer.database: postgresql`），带 `psycopg` / `psycopg-pool` |
| `aiosqlite`（`>=0.22.1`） | `SQLiteAdapter` 与 `meme_extension.MemeSqlite` 共用的异步 sqlite 驱动（连接分别由 `close()` / `__aexit__` 关） |
| `aiofiles`（`>=24.1.0`） | `base_system_tools` 的 `write` / `replace` 工具异步写盘（`aiofiles.open` + `async with`） |
| `psycopg`（`>=3.3.6`）/ `psycopg-pool`（`>=3.3.3`） | `PostgresqlAdapter` 直接 import 的驱动与连接池（`AsyncConnectionPool`） |
| `pydantic`（`>=2.13.5`） | 配置模型（`BaseModel` / `Field` / `model_validator`）与工具参数 schema |
| `pyyaml`（`>=6.0.3`） | `core/plugin_loader.py` 读子插件 `config.yaml` 的 `yaml.safe_load` |
| `filetype`（`>=1.2.0`） | `base_system_tools` 的图片类型嗅探（`read_image`） |

> 注：以上依赖由 `manifest.toml` 的 `pip_dependencies` 声明。
> 注：0.7.0 及以前依赖 `pi_bridge` 与外部 pi Agent 进程，0.8.0 起已整体移除。

## 项目状态

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
