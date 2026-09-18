# miaoli_bot

一个基于 [Ncatbot](https://github.com/NapNeko/NcatBot) 的 QQ 机器人插件，将 **pi**（`pi_bridge` 桥接的 LLM Agent）接入 QQ 对话服务，让 QQ 消息驱动 agent 思考、回复并调用工具。

- **版本**：0.7.0
- **入口**：`main.py`（插件类 `MiaoLiBot`）
- **运行载体**：Ncatbot 插件系统（NapCat/OneBot 协议）

## 功能特性

- 🧠 **LLM 接入 QQ**：通过 `pi_bridge.PiClient` 与 pi Agent 通信，QQ 私聊/群聊消息直接进入 agent 会话（`PiClient.open(session_id=…, session_dir=…, system_prompt=…)` + `set_model(provider=…, model_id=…)` 完成初始化，参数全部来自插件配置模型）。
- 🎛️ **配置化建会话**：`config.yaml`（插件目录默认值，全局 `plugin_configs.miaoli_bot` 同键覆盖）在 `on_load` 里解析为 pydantic 模型 `models.PluginConfig`（字段名即配置键名：`model_id` / `provider` 必填，`session_dir` / `system_prompt` / `prompt_file` 可选，未声明的键由 `extra="allow"` 承载）；`main.MiaoLiBot.create_pi_factory(session_id)` 从 `self.cfg` 闭包出无参异步工厂交给 `ensure_session`，会话命中时工厂不会被调用。**必填项缺失会在插件加载时报 `ValidationError`**（fail-fast，不再是首条消息时的 `KeyError`）。
- 🧹 **关闭兜底清理**：`protocols/closable.py` 的 `Closable` 运行时协议（只声明 `async def close()`）让 `on_close` 能对 `SHARE_STORE` 做统一兜底清理（`main.MiaoLiBot.clean_share_store`）——实现 `Closable` 的逐个 `close()`、close 后 double-check 并 `drop` 残留键、失败只记 warning 不中断；**兜底清理不代表可以不清理**，已知资源的显式清理仍是第一责任。
- 🔀 **会话隔离**：`core.PiSessionManager` 按 `session_id` 管理 `PiClient` 实例（`await session_manager.ensure_session(session_id, *, timeout=60.0, factory=…)`，未命中且缺 `factory` 抛 `MissFactoryError`；`close()` 幂等关闭）——群聊键为 `group-<group_id>`、私聊键为 `private-<user_id>`（`utils.concatenate_id`），命中复用、未命中才建客户端，同一会话建连在 per-session `asyncio.Lock` 内串行，各群 / 私聊持有独立客户端与会话。
- 🔔 **事件优先级让位**：`on_message` 以 `priority=-100` 注册，排在后处理的位置 —— 扩展插件可先用更高优先级接收事件（如 `miaoli_like` 的 `赞我`：`priority=100`）并停止事件传播，被上游截下的消息不会再进入 LLM，修复「私聊发送 `赞我` 时机器人除此之外还当作普通对话重复回复一次」的问题。
- ⚡ **流式事件驱动**：逐帧消费 pi 的事件流，用 `utils/pi_event_classifier.py` 区分正文增量（`TextDeltaEvent`）、思维链增量（`ThinkingDeltaEvent`）、agent 结束（`AgentSettledEvent`）与错误事件。正文按 `\n\n` 分块实时发回 QQ，本轮结束回复 `[DONE]`。
- 🎭 **角色扮演**：内置猫娘「喵璃」人设提示词（`data/prompt_v1.1.md`），agent 输出由插件自动发送，仅在需要图片/文件/AT/引用/跨会话时才调用发消息工具。
- 🧭 **流式期间可干预**：agent 正在输出时收到新消息，由客户端本地 `asyncio.Lock` 判定忙闲后以 `steer` 注入而非另起一轮（`prompt(i_data, streamingBehavior="steer")`），避免同一事件流被多个 Task 重复订阅。
- 🖼️ **多类型消息段**：`SegmentParseChain` 支持文本 / AT / 图片 / 文件 / 引用五类消息段（`Text` / `At` / `Image` / `File` / `Reply`），分别产出 `{text}`、`{at}`、`{image, size}`、`{image, size}`、`{reply}`。
- 🧠 **会话记忆外部托管**：插件不做本地持久化，会话上下文由外部 PI AGENT 进程管理（`session_dir` 指定）。
- 🛠️ **工具调用闭环**：通过 `core.PIToolBackend` 把 QQ 侧能力（发消息 `send_message_to_QQ`、下载文件 `download_qq_file`、查消息 `query_qq_message_id`、撤回消息 `delete_qq_message`）注册为 pi 可调用的工具；后端配置经 `SHARE_STORE` 的 `PLUGIN_CONFIG`（`PluginConfig` 实例）按属性读取（`getattr`，键名写错会响亮报错）。
- 🧩 **两级解析链**：`EventParseChain`（群/私聊事件元数据）与 `SegmentParseChain`（文本/AT/图片/文件/引用消息段）双链分发，`utils/easier_parser.parse_message` 一步合并产出完整消息结构（元数据 + message 段数组）喂给 agent。
- 🦆 **鸭子类型适配**：`adapters/EventAdapter` 不依赖具体 ncatbot 类型，通过属性探测兼容不同消息事件形态。
- 💾 **共享存储**：`stores/SHARE_STORE` 全局共享容器，键集中定义于 `consts/share_store_keys.py`（EVENT_PARSER / SEGMENT_PARSER / NCATBOT_API / PLUGIN_CONFIG（插件配置模型实例）/ RAW_CONFIG（ncatbot 合并后的原始配置 dict）/ TOOL_BACKEND / PI_SESSION_MANAGER）。
- 🔧 **协议先行**：`protocols/` 定义 `Parser`（鸭子类型协议）、`Closable`、`ChainProtocol`、`StoreProtocol`，其中 `Parser` / `Closable` 带 `@runtime_checkable`（可 `isinstance` 判定，`Closable` 即兜底清理的判定依据），业务实现均依赖接口。
- 🧪 **本地测试**：`tests/` 目录提供按模块划分的 pytest 用例（不随仓库提交，全量 147 例），`utils.easier_parser`、解析链、适配器、工具组装、`PiSessionManager` 并发不变量、`PluginConfig` 配置模型（含与真实 `config.yaml` 的字段对齐守卫）与 `_Prompt` 事件流包装（WIP）均有覆盖。

## 架构设计

```
QQ / NapCat (OneBot)
        │ ncatbot 事件
        ▼
main.py  MiaoLiBot(NcatBotPlugin)    ← config.yaml → models.PluginConfig（model_id / provider / session_dir / prompt_file）
        │ parse_message（easier_parser 合并 event + segment 两级解析）
        ▼
parsers/  EventParseChain → Group/PrivateMessageEventParser（事件元数据）
          SegmentParseChain → Text/At/Image/File/ReplySegmentParser（消息段）
        │ 统一 dict：{platform / from_group / created_at / group / sender / message: [...]}
        ▼
adapters/  EventAdapter（鸭子类型适配 ncatbot 事件：user_id / group_id / is_group / send）
        │
        ▼
core/PiSessionManager.ensure_session(session_id)   ← SHARE_STORE(PI_SESSION_MANAGER)
        │  会话键 = group- / private- + target_id（utils.concatenate_id）
        │  命中 → 复用已建 PiClient；未命中 → 调用 create_pi_factory 产出的工厂建连并缓存
        ▼
core/PiClient.prompt() ────────────►  pi_bridge.PiClient ──►  pi Agent（LLM）
        │  _stream_lock 已持有时改走 steer() 注入                        │ 工具调用
        │ 事件流（Text/ThinkingDelta, AgentSettled）                 ▼
utils/pi_event_classifier 分类 ◄───          core/PIToolBackend._execute_tool
        │                                              │
        ▼                                              ├─ tools/send_message.py   (send_message_to_QQ)
   发送到 QQ（easier_send）                            ├─ tools/download_file.py  (download_qq_file)
                                                       ├─ tools/query_message_id.py (query_qq_message_id)
                                                       └─ tools/delete_message.py (delete_qq_message)
```

### 目录结构

```
miaoli_bot/
├── main.py                        # 插件入口：MiaoLiBot，注册两级解析链与工具后端
├── manifest.toml                  # 插件清单（name/version/entry_class）
├── config.yaml                    # 插件配置默认值（model_id / provider / session_dir / prompt_file）
├── adapters/                      # ncatbot 事件鸭子类型适配器
│   ├── base_adapter.py            #   BaseAdapter 基类
│   └── event_adapter.py           #   EventAdapter（user_id/group_id/is_group/send）
├── chains/                        # 责任链实现
│   ├── base_chain.py              #   BaseParserChain：注册 + 分发给首个接受的 parser（短路）
│   ├── event_parse_chain.py       #   EventParseChain
│   └── segment_parse_chain.py     #   SegmentParseChain
├── consts/                        # 常量集中定义
│   ├── id_prefix.py               #   会话键前缀（group- / private-）
│   └── share_store_keys.py        #   SHARE_STORE 键名（EVENT_PARSER/SEGMENT_PARSER/PI_SESSION_MANAGER/RAW_CONFIG/...）
├── core/                          # pi 桥接层
│   ├── pi_client.py               #   PiClient：prompt 流式接口，asyncio.Lock 保证单订阅者，忙时按 streamingBehavior 走 steer/follow_up
│   ├── _prompt.py                 #   _Prompt：事件流包装（按类型注册回调 / aclose / async with），WIP 未接入 PiClient
│   ├── pi_session_manager.py      #   PiSessionManager：按 session_id 建/取/关 PiClient（ensure_session(timeout=, factory=) / close()），per-session 锁 + 内置 MissFactoryError 契约
│   └── pi_tool_backend.py         #   PIToolBackend：从 SHARE_STORE 的 PLUGIN_CONFIG 模型按属性读 host/port，记录工具调用
├── data/                          # 提示词资产（prompt_v1.0.md / prompt_v1.1.md）
├── enums/                         # 枚举定义
├── errors/                        # 异常定义
│   ├── base_bot_error.py          #   BaseBotError 基类
│   ├── pi_prompt_busy_error.py    #   PIPromptBusyError（pi 忙且未指定 streamingBehavior）
│   ├── session_manager_closing_error.py # SessionManagerClosingError（关闭中仍请求建会话）
│   └── miss_factory_error.py      #   MissFactoryError（未命中会话且未传 factory）
├── models/plugin_config.py        #   PluginConfig：插件配置的 pydantic 模型（字段名即配置键名，extra 键放行）
├── models/runtimes/               # 运行时数据模型
│   ├── dispatch_result.py         #   DispatchResult（链调度结果）
│   └── parse_result.py            #   ParseResult（parse_message 合并结果：event + segments）
├── parsers/                       # 解析器实现
│   ├── event_parsers/             #   Group/PrivateMessageEventParser
│   └── segment_parsers/           #   Text/At/Image/File/ReplySegmentParser
├── protocols/                     # 抽象协议：Parser / Closable / ChainProtocol / StoreProtocol
├── stores/                        # 全局共享存储（SHARE_STORE）
├── tools/                         # 暴露给 pi 的工具（发消息 / 下载 QQ 文件 / 查询消息 / 撤回消息）
├── tests/                         # 本地 pytest 用例（gitignore，不提交）
└── utils/                         # 工具函数
    ├── easier_parser.py           #   parse_event / parse_segment / parse_message 快捷入口
    ├── easier_sender.py           #   private/group 便捷发送封装
    ├── event_ops.py               #   从事件取 id（群→group_id，私聊→user_id）
    ├── pi_event_classifier.py     #   pi 事件分类（text/thinking 增量、agent 结束/错误）
    └── sugar.py                   #   concatenate_id（会话键加 group- / private- 前缀）
```

## 数据流

1. QQ 消息经 NapCat → ncatbot → 按注册优先级分发给各插件：本插件以 `priority=-100` 排在后面，若上游插件（如 `miaoli_like` 的 `赞我`）已停止事件传播，本条消息不会到达这里，流程到此结束。
2. `on_message` 调用 `parse_message`：`EventParseChain` 解析事件元数据（群 → `GroupMessageEventParser`，私聊 → `PrivateMessageEventParser`），`SegmentParseChain` 逐段解析 `message`（文本 → `TextSegmentParser`，AT → `AtSegmentParser`，图片 → `ImageSegmentParser`，文件 → `FileSegmentParser`，引用 → `ReplySegmentParser`），合并为统一 dict（`platform`、`from_group`、`created_at`、`group`、`sender`、`message: [...]`）。
3. `session_id = concatenate_id(target_id, is_group=is_group)`（群 → `group-<group_id>`，私聊 → `private-<user_id>`）后调用 `PiSessionManager.ensure_session`：命中已有会话直接复用 `PiClient`；未命中则在 per-session 锁内惰性调用传入的工厂 —— 工厂由 `create_pi_factory` 依 `self.cfg`（`PluginConfig`，来自 `config.yaml`）闭包出 `PiClient.open(session_id=…)` + `set_model(provider=…, model_id=…)`，建连超时上限由 `timeout`（默认 60s）控制。未命中且未传 `factory` 抛 `MissFactoryError`，管理器关闭中抛 `SessionManagerClosingError`。
4. `PiClient.prompt(i_data, streamingBehavior="steer")` 将解析结果送入 pi Agent，流式返回事件；`prompt` 内部先检查本地 `_stream_lock`，若 agent 正在输出则改走 `steer()` 注入新消息并直接返回（不产生事件流），未指定 `streamingBehavior` 时抛 `PIPromptBusyError`。
5. `pi_event_classifier` 分类事件：正文增量实时回发 QQ；agent 结束即回复 `[DONE]` 并结束本轮；出错记录日志。
6. agent 需要调用工具时，经 `PIToolBackend` 执行 `send_message_to_QQ` / `download_qq_file` / `query_qq_message_id` / `delete_qq_message`，结果回流给 agent。
7. 插件卸载（`on_close`）：先显式 `drop` 掉 `NCATBOT_API` / `PLUGIN_CONFIG` / `RAW_CONFIG`，再依次关闭工具后端与 `PiSessionManager`（`_close_session_manager()` 为显式调用），最后由 `clean_share_store()` 对 `SHARE_STORE` 做兜底清理 —— 实现 `Closable` 的键逐个 `close()`，close 后仍留在容器的键 `drop` 掉（已被对象自行摘除则记 warning），全程逐键记日志。

## 安装与使用

1. 将本目录放入 ncatbot 的插件目录（如 `plugins/miaoli_bot`）。
2. 确认运行环境已安装依赖：
   - `ncatbot`
   - `pi_bridge`（参见 [pi-bridge](https://github.com/lyt2011/pi-bridge)）
   - `pytest` / `pytest-asyncio`（仅本地跑测试需要）
3. 插件配置（插件目录 `config.yaml` 为默认值，全局 `config.yaml` 的 `plugin.plugin_configs.miaoli_bot` 同键覆盖）：

配置键名与 `models.PluginConfig` 的字段一一对应，在插件加载时（`on_load`）解析校验：必填项缺失 / 类型不符会抛 `ValidationError`，本插件加载失败并在日志留下 traceback（机器人的其余部分不受影响）。

| 键 | 默认 / 必填 | 用途 |
|---|---|---|
| `model_id` | **必填** | `set_model(provider=…, model_id=…)` 的模型名（示例：`deepseek-flash`） |
| `provider` | **必填** | 模型供应商（示例：`deepseek-official`） |
| `session_dir` | `gettempdir()`（`/tmp`） | `PiClient.open` 的会话目录（上下文由外部 PI AGENT 进程托管） |
| `prompt_file` | 优先读 | 系统提示词文件路径，加载时读取（UTF-8）并写入 `system_prompt`（示例配置：`data/prompt_v1.1.md`） |
| `system_prompt` | 回退 | 内联系统提示词，仅在未配置 `prompt_file` 时使用（可为 `null`） |
| `buffer_limit` | `32 * 1024 * 1024` | `PiClient.open` 的事件缓冲上限（extra 键：不是模型字段，示例配置未显式给出时由 `create_pi_factory` 兜底） |
| `tool_backend_host` / `tool_backend_port` | `127.0.0.1:39999`（`PTBACKEND_HOST` / `PTBACKEND_PORT`） | `core/PIToolBackend` 经 `SHARE_STORE` 的 `PLUGIN_CONFIG`（模型实例）按属性读取，留空则由 pi_bridge 取环境变量默认值 |
4. 启动 bot，在 QQ 中私聊或群聊即可与 agent 对话。

### 本地测试

```bash
cd <插件父目录>          # plugins/
<venv>/bin/python -m pytest miaoli_bot/tests/ -v
```

## 依赖

| 包 | 用途 |
|---|---|
| `ncatbot` | QQ 机器人框架 / 事件与消息 API |
| `pi_bridge` | pi 与 Python 的桥接层（`PiClient` / `PIToolBackend`，v0.6.0+） |

> 注：`manifest.toml` 中 `pip_dependencies` 声明插件依赖（`ncatbot5` / `pi_bridge`），也可在运行环境中自行安装。
> 注：`pi_bridge` 0.6.0 起 `prompt` 请求被拒时会抛 `RequestRefuseError`，本插件**暂未捕获**（异常会冒到 ncatbot 事件处理器，日志有 traceback、用户侧无回复），详见 CHANGELOG 0.5.4。

## 项目状态

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
