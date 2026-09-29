# miaoli_bot

一个基于 [Ncatbot](https://github.com/NapNeko/NcatBot) 的 QQ 机器人插件，用 **LangGraph** 自建图管线把 QQ 对话接给 LLM，让 QQ 消息驱动模型思考、回复并调用工具。

- **版本**：0.8.0
- **入口**：`main.py`（插件类 `MiaoLiBot`）
- **运行载体**：Ncatbot 插件系统（NapCat/OneBot 协议）
- **LLM 客户端**：`langchain-openai` 的 `ChatOpenAI`（`base_url` 指向任意 OpenAI 兼容端点）
- **阶段**：重构完成，当前处于**优化态** —— 架构骨架已立住，后续以补齐功能、补错误处理、优化体验为主

## 功能特性

- 🧩 **自建图管线**：`core.GraphPipeline`（泛型 `GraphPipeline[StateT, ContextT, InputT, OutputT]`，四个 TypeVar 取自 `langgraph.typing`）把「事件 → 处理器」的编排从 `main.py` 抽成独立类 —— 8 个图事件常量集中在 `consts/graph.py`，节点用 `register(event, node, priority=0)` **显式**挂载（同一事件可挂多个，按 `priority` 排序），`wire()` 一次性产出 8 节点 + 8 条边，`compile(checkpointer=…)` 出 `CompiledStateGraph`。**「谁挂在哪个事件上」在 `main.py._build_graph` 里一眼可见**。
- 🧠 **LLM 接入**：`ChatOpenAI` 经 `models.GraphRuntimeContext` 的 `chat_model` 注入图；`call_llm` 节点用 `bind_tools(TOOLS)` 后请求模型；工具循环由 `tools_condition` 条件边在「有 `tool_calls` → 执行工具 → 回到请求」与「无 `tool_calls` → 收尾」之间自动分流。
- 📜 **状态与上下文分离**：`models.GraphState`（进 checkpoint 的会话状态）与 `models.GraphRuntimeContext`（不进 checkpoint 的运行时依赖）。`context` 不进 checkpoint、不做浅拷贝、结果保持原引用，所以 LLM 客户端 / 锁这类不可序列化对象只能放 `context`；`messages` 是唯一带 reducer（`add_messages`）的键，天然累加，**不需要手动保存历史**。
- 🎛️ **配置模型化（分层）**：`PluginConfig` 由平铺字段改为分层 —— `providers: [Provider(name / base_url / api_key / models: [LLM(name / context_window / max_tokens)])]` 加 `account_config`（`bot_id` / `root_id` / `bot_nickname` / `root_nickname`，四项全必填）、`meme_config`、`output_config`、`session_dir`（`DirectoryPath`）/ `prompt_file`（`FilePath`）/ `system_prompt`。路径类型让 `prompt_file` 指向不存在的文件在**加载期**就报错，`account_config` 缺失即 `ValidationError`（fail-fast，不再等到首条消息 `KeyError`）。
- 🛠️ **工具调用闭环**：8 个工具 —— 发消息 `send_message_to_qq`、发文件 `send_file_to_qq`、发表情包 `send_meme_to_qq`、列表情包 `list_memes`、归档表情包 `archive_meme`、下载 QQ 文件 `download_qq_file`、查消息 `query_qq_message_id`、撤回消息 `delete_qq_message`。统一由 `ToolNode` 执行，返回值经 `utils.tool_result_builder` 的 `success` / `fail` / `custom` 收敛成 `{"status": bool, "message": …}`。
- 🧩 **两级解析链**：`EventParseChain`（群 / 私聊事件元数据）与 `SegmentParseChain`（文本 / AT / 图片 / 文件 / 引用消息段）双链分发，`utils.easier_parser.parse_message` 一步合并产出 `ParseResult(event, segments)` 喂给图。
- 🖼️ **多类型消息段**：`Text` → `{text}`、`At` → `{at}`、`Image` → `{image, size}`、`File` → `{file, size}`、`Reply` → `{reply}`。
- 🦆 **鸭子类型适配**：`adapters/EventAdapter` 不依赖具体 ncatbot 类型，通过属性探测兼容不同消息事件形态（`user_id` / `group_id` / `is_group` / `send`）；`utils.get_id_from_event` 群取 `group_id`、私聊取 `user_id`。
- 🔧 **协议先行**：`protocols/` 定义 `Parser` / `Closable` / `ChainProtocol` / `StoreProtocol`，其中 `Parser` 与 `Closable` 带 `@runtime_checkable`（可 `isinstance` 判定，`Closable` 即兜底清理的判定依据），业务实现均依赖接口。
- 🧹 **关闭兜底清理**：`on_close` 先显式 `drop` 已知键，再对 `SHARE_STORE` 做快照遍历（`main.MiaoLiBot.clean_share_store`）—— 实现 `Closable` 的逐个 `close()`、close 后仍留在容器的 `drop` 掉、失败只记 warning 不中断。**兜底清理不代表可以不清理**，已知资源的显式清理仍是第一责任。
- 💾 **共享存储**：`stores/SHARE_STORE` 全局共享容器，键集中定义于 `consts/share_store_keys.py`（`EVENT_PARSER` / `SEGMENT_PARSER` / `NCATBOT_API` / `PLUGIN_CONFIG`（配置模型实例）/ `RAW_CONFIG`（ncatbot 合并后的原始 dict）/ `PLUGIN_DIR` / `WORKSPACE_DIR`（ncatbot 分配的插件数据目录）/ `GRAPH_PIPELINE`）。
- 🔔 **事件优先级让位**：`on_message` 以 `priority=-100` 注册，排在后处理的位置 —— 扩展插件可用更高优先级抢先接收并停止事件传播（如 `miaoli_like` 的 `赞我` 用 `priority=100`），被上游截下的消息不会再进入 LLM。
- 🎭 **角色扮演**：内置猫娘「喵璃」人设提示词（`data/prompts/prompt_v1.3.md`，另有 v1.0 ~ v1.2 历史版本）；`format_prompt` 节点把人设与管理员 / 机器人的 QQ 号、昵称拼成 `<account>` 标签块，一起写进系统提示词。
- 🧪 **本地测试（待重写）**：`tests/` 目录（gitignore，不随仓库提交）里的用例针对的是 pi 桥接层，随 0.8.0 重构整体失效。

## 架构设计

```
QQ / NapCat (OneBot)
        │ ncatbot 事件
        ▼
main.py  MiaoLiBot(NcatBotPlugin)      ← config.yaml → models.PluginConfig（providers / account_config / …）
        │   ① parse_message（easier_parser 合并 event + segment 两级解析）
        │   ② EventAdapter.build(event) + concatenate_id → session_id（thread_id）
        ▼
parsers/  EventParseChain → Group / PrivateMessageEventParser
          SegmentParseChain → Text / At / Image / File / ReplySegmentParser
        │   → ParseResult(event, segments)
        ▼
core/GraphPipeline.ainvoke({"event", "segments"}, thread_id=session_id, context=…)
        │
        │  START
        ▼
   ON_AGENT_START
        ▼
   ON_TURN_START ── format_input（event + segments → HumanMessage，追加进 messages）
        │           format_prompt（<account> 信息块 + 人设 → system_prompt 键）
        ▼
   ON_BEFORE_REQUEST ──▶ ON_REQUEST ── call_llm ──▶ bind_tools(TOOLS) → ChatOpenAI
        ▲                    │                            │
        │                    │                            ▼
        │           ON_AFTER_REQUEST             AIMessage（含 tool_calls）
        │                    │
        │  tools_condition   ├── 有 tool_calls ──▶ ON_TOOL_CALLING ── ToolNode → ToolMessage
        │                    │                     （回到 ON_BEFORE_REQUEST）
        └────────────────────┴── 无 tool_calls ──▶ ON_TURN_END ── last_msg_to_answer
                                                        ▼         （messages[-1] → final_answer）
                                                   ON_AGENT_END
                                                        ▼
                                                       END

        │  output["final_answer"]
        ▼
adapters/EventAdapter.send(api, …)  ──▶  QQ
```

### 目录结构

```
miaoli_bot/
├── main.py                        # 插件入口：MiaoLiBot（建图 + 注册两级解析链 + TOOLS 列表）
├── manifest.toml                  # 插件清单（name / version / entry_class / pip_dependencies）
├── config.example.yaml            # 配置模板（config.yaml 已 gitignore，内含密钥不提交）
├── adapters/                      # ncatbot 事件鸭子类型适配器
│   ├── base_adapter.py            #   BaseAdapter 基类
│   └── event_adapter.py           #   EventAdapter（user_id / group_id / is_group / send）
├── chains/                        # 责任链实现
│   ├── base_chain.py              #   BaseParserChain：注册 + 分发给首个接受的 parser（短路）
│   ├── event_parse_chain.py       #   EventParseChain
│   └── segment_parse_chain.py     #   SegmentParseChain
├── consts/                        # 常量集中定义
│   ├── graph.py                   #   8 个图事件名（ON_TURN_START 等）+ MAX_PRIORITY / MIN_PRIORITY
│   ├── id_prefix.py               #   会话键前缀（group- / private-）
│   └── share_store_keys.py        #   SHARE_STORE 键名
├── core/                          # 图管线与节点
│   ├── graph_pipeline.py          #   GraphPipeline：register / wire / compile / ainvoke / _dispatch / _merge
│   ├── nodes.py                   #   5 个图节点（format_input / format_prompt / call_llm / on_tool_calling / last_msg_to_answer）
│   └── meme_manager.py            #   MemeManager
├── data/prompts/                  # 提示词资产（prompt_v1.0.md ~ prompt_v1.3.md）
├── errors/                        # 异常定义
│   ├── base_bot_error.py          #   BaseBotError 基类
│   ├── api_unavailable_error.py   #   APIUnavailableError（工具里 api 不可用时抛）
│   └── session_manager_closing_error.py # SessionManagerClosingError
├── models/                        # 数据模型
│   ├── plugin_config.py           #   PluginConfig / Provider / LLM / AccountConfig / MemeConfig / OutputConfig
│   ├── graph_state.py             #   GraphState（进 checkpoint：event / segments / messages / final_answer / system_prompt）
│   ├── graph_runtime_context.py   #   GraphRuntimeContext（不进 checkpoint：plugin_config / chat_model / tools）
│   └── runtimes/                  #   Handler（图处理器登记单元）/ ParseResult / DispatchResult
├── parsers/                       # 解析器实现
│   ├── event_parsers/             #   Group / PrivateMessageEventParser
│   └── segment_parsers/           #   Text / At / Image / File / ReplySegmentParser
├── protocols/                     # 抽象协议：Parser / Closable / ChainProtocol / StoreProtocol
├── stores/                        # 全局共享存储（SHARE_STORE）
├── tools/                         # 8 个暴露给 LLM 的工具
├── tests/                         # 本地 pytest 用例（gitignore，不提交；当前待重写）
└── utils/                         # 工具函数
    ├── easier_parser.py           #   parse_event / parse_segment / parse_message 快捷入口
    ├── easier_sender.py           #   private / group 便捷发送封装
    ├── event_ops.py               #   get_id_from_event（群 → group_id，私聊 → user_id）
    ├── meme_sqlite_ops.py         #   meme 的 sqlite 连接与建表
    ├── sugar.py                   #   concatenate_id（会话键加 group- / private- 前缀）
    └── tool_result_builder.py     #   custom / success / fail（工具返回值统一契约）
```

## 数据流

1. QQ 消息经 NapCat → ncatbot → 按注册优先级分发给各插件：本插件以 `priority=-100` 排在后面，若上游插件（如 `miaoli_like` 的 `赞我`）已停止事件传播，本条消息不会到达这里，流程到此结束。
2. `on_message` 先判 `@`（群消息必须 @ 到机器人，`all_except=True`），再调 `parse_message`：`EventParseChain` 解析事件元数据（群 → `GroupMessageEventParser`，私聊 → `PrivateMessageEventParser`），`SegmentParseChain` 逐段解析 `message`（文本 / AT / 图片 / 文件 / 引用），合并为 `ParseResult(event, segments)`。
3. `session_id = concatenate_id(target_id, is_group=is_group)`（群 → `group-<group_id>`，私聊 → `private-<user_id>`），作为 LangGraph 的 `thread_id` —— 同一会话的 `messages` 由 checkpointer（`InMemorySaver`）按 `thread_id` 累积，跨轮记忆不需要插件自己做。
4. `graph_pipeline.ainvoke({"event": …, "segments": …}, thread_id=session_id, context={"plugin_config": self.cfg, "chat_model": …, "tools": TOOLS})`。
5. 图内 `ON_TURN_START`：`format_input` 把 `event` + `segments` 序列化成 JSON 文本包成 `HumanMessage` **追加**进 `messages`（`add_messages` reducer 保证累加）；`format_prompt` 把 `<account>` 信息块 + 人设写入 `system_prompt` 键（普通键，每轮覆盖 —— **静态内容不追加，否则每轮多一份**）。
6. `ON_REQUEST` 的 `call_llm`：`runtime.context["chat_model"].bind_tools(runtime.context["tools"])` 后以 `[SystemMessage(state["system_prompt"]), *state["messages"]]` 请求模型（**系统提示词拼在副本最前，不动 `state["messages"]`**），返回的 `AIMessage` 追加进 `messages`。
7. `ON_AFTER_REQUEST` 由 `tools_condition` 分流：有 `tool_calls` → `ON_TOOL_CALLING` 的 `on_tool_calling` 用 `ToolNode(runtime.context["tools"])` 执行工具、`ToolMessage` 追加进 `messages`，回到 `ON_BEFORE_REQUEST` 再请求一次；无 `tool_calls` → `ON_TURN_END`。
8. `ON_TURN_END` 的 `last_msg_to_answer` 取 `messages[-1]`，是 `AIMessage` 就把 `content` 写进 `final_answer`（否则回退成固定文案）。
9. `on_message` 拿 `output["final_answer"]` 交给 `EventAdapter.send(self.api, …)` 发回 QQ。
10. 插件卸载（`on_close`）：先显式 `drop` 掉 `NCATBOT_API` / `PLUGIN_CONFIG` / `RAW_CONFIG` / `PLUGIN_DIR` / `WORKSPACE_DIR` / `GRAPH_PIPELINE`，再由 `clean_share_store()` 对 `SHARE_STORE` 兜底清理 —— 实现 `Closable` 的键逐个 `close()`，close 后仍留在容器的 `drop` 掉（已被对象自行摘除则记 warning），全程逐键记日志。

## 安装与使用

1. 将本目录放入 ncatbot 的插件目录（如 `plugins/miaoli_bot`）。
2. 确认运行环境已安装依赖（`manifest.toml` 的 `pip_dependencies` 会在 `plugin.auto_install_pip_deps` 打开时自动安装）：
   - `ncatbot`（`>=5.5.8`）
   - `langgraph`（`>=1.2.12`）
   - `langchain-openai`（`>=1.6.6`）
3. 插件配置：`cp config.example.yaml config.yaml` 后填真实 `api_key`（`config.yaml` 含密钥、已 gitignore）。插件目录的 `config.yaml` 为默认值，全局 `config.yaml` 的 `plugin.plugin_configs.miaoli_bot` 同键覆盖；`on_load` 第一步即 `PluginConfig.model_validate(self.config)`，必填项缺失 / 路径不存在 / 类型不符都会抛 `ValidationError`，本插件加载失败并在日志留下 traceback（机器人其余部分不受影响）。

配置键名与 `models.PluginConfig` 的字段一一对应：

| 键 | 默认 / 必填 | 用途 |
|---|---|---|
| `providers` | `[]` | 供应商列表，每项 `Provider(name / base_url / api_key / models)` |
| `providers[].base_url` | **必填** | 请求地址（**不会拼路径**，填到 `/v1` 这一层） |
| `providers[].api_key` | **必填** | 鉴权密钥 |
| `providers[].models` | `[]` | 模型列表，每项 `LLM(name / context_window / max_tokens)` |
| `account_config` | **必填** | `bot_id` / `root_id` / `bot_nickname` / `root_nickname`，四项全必填；`format_prompt` 用它拼 `<account>` 提示词块 |
| `session_dir` | `gettempdir()`（`/tmp`） | 会话保存路径（`DirectoryPath` 校验存在性） |
| `prompt_file` | `null` | 系统提示词文件（`FilePath` 校验存在性，加载时按 UTF-8 读入），优先于 `system_prompt` |
| `system_prompt` | `null` | 内联系统提示词，仅在未配置 `prompt_file` 时使用（可为 `null`） |
| `meme_config` | `MemeConfig()` | `is_enable`（默认 `false`）/ `sqlite_path` / `max_memes`；**可以关闭 + 传路径，不能启用 + 不传路径**（`model_validator` 拒绝） |
| `output_config` | `OutputConfig()` | **Future 占位**（字段已定，暂无消费方）：`typing_speed`（默认 `0.01`）/ `typing_speed_offset`（默认 `0`）/ `split_separator`（默认 `""`）—— 以后用于把回复切块并按字数模拟打字延迟 |

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

> 注：以上三个由 `manifest.toml` 的 `pip_dependencies` 声明。
> 注：0.7.0 及以前依赖 `pi_bridge` 与外部 pi Agent 进程，0.8.0 起已整体移除。

## 项目状态

v0.8.0 — **移除 `pi_bridge`，改用 LangGraph 自建图管线（破坏性重构）**：删除 `core/pi_client.py` / `pi_session_manager.py` / `pi_tool_backend.py` / `_prompt.py`、`utils/pi_event_classifier.py`、`errors/miss_factory_error.py` / `pi_prompt_busy_error.py` 与 `enums/` 目录，`manifest.toml` 的依赖改为 `langgraph` + `langchain-openai`；新增 `core/graph_pipeline.py`（`GraphPipeline`：`register(event, node, priority)` 显式挂载 + `wire()` 一次成型 + `_dispatch` 按优先级串行并对返回值做增量合并）、`consts/graph.py`（8 个图事件 + `MAX/MIN_PRIORITY`）、`core/nodes.py`（5 个节点）、`models/graph_state.py`（进 checkpoint 的会话状态）与 `models/graph_runtime_context.py`（不进 checkpoint 的运行时依赖）；`PluginConfig` 重构为分层结构（`providers` / `account_config`（必填）/ `meme_config` / `output_config` + `session_dir` / `prompt_file` / `system_prompt`），**配置结构与共享键均不向下兼容**（`plugin_configs.miaoli_bot` 需整块重写）；工具由 4 个扩到 8 个（新增 `send_file_to_qq` / `send_meme_to_qq` / `list_memes` / `archive_meme`），返回值统一走 `utils.tool_result_builder`；`config.yaml` 改由 `config.example.yaml` 作入库模板；`parsers` 的 `file_parser` 返回值键由 `image` 修正为 `file`（**破坏性**）；`main.py` / `models` / `utils` / `consts` / `errors` 的导出表全部同步。**重构完成，进入优化态**，后续迭代项：`OutputConfig` 是预留占位（字段已定、暂无消费方，见 Future）；`main.py` 的 `chat_model` 仍是每条消息 new 一个 `ChatOpenAI` 的 `# HACK`；`GraphPipeline._dispatch` 暂无错误处理、`_build_graph` 写 `SHARE_STORE` 未持 `store_lock`；本地 147 例用例整体失效待重写。（另：三处漏 import 的注解 `Union` / `List` 已补齐 —— Python 3.14 的注解延迟求值让「漏 import 类型」不再报 `NameError` 而是静默失效，只有 pydantic 这种必须解析注解建 schema 的使用方才会炸，详见 CHANGELOG 0.8.0 的 Note。）

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
