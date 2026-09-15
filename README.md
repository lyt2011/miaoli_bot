# miaoli_bot

一个基于 [Ncatbot](https://github.com/NapNeko/NcatBot) 的 QQ 机器人插件，将 **pi**（`pi_bridge` 桥接的 LLM Agent）接入 QQ 对话服务，让 QQ 消息驱动 agent 思考、回复并调用工具。

- **版本**：0.3.0
- **入口**：`main.py`（插件类 `Claw`）
- **运行载体**：Ncatbot 插件系统（NapCat/OneBot 协议）

## 功能特性

- 🧠 **LLM 接入 QQ**：通过 `pi_bridge.PiClient` 与 pi Agent 通信，QQ 私聊/群聊消息直接进入 agent 会话（`PiClient.open(session_dir="/tmp/", system_prompt=data/prompt_v1.1.md)` + `set_model(...)` 完成初始化）。
- ⚡ **流式事件驱动**：逐帧消费 pi 的事件流，用 `utils/pi_event_classifier.py` 区分正文增量（`TextDeltaEvent`）、思维链增量（`ThinkingDeltaEvent`）、agent 结束（`AgentSettledEvent`）与错误事件。正文按 `\n\n` 分块实时发回 QQ，本轮结束回复 `[DONE]`。
- 🎭 **角色扮演**：内置猫娘「喵璃」人设提示词（`data/prompt_v1.1.md`），agent 输出由插件自动发送，仅在需要图片/文件/AT/引用/跨会话时才调用发消息工具。
- 🧭 **流式期间可干预**：agent 正在输出时收到新消息，由客户端 `get_state()` 判定 `isStreaming` 后以 `steer` 注入而非另起一轮（`prompt(i_data, streamingBehavior="steer")`），避免同一事件流被多个 Task 重复订阅。
- 🖼️ **多类型消息段**：`SegmentParseChain` 支持文本 / AT / 图片 / 文件 / 引用五类消息段（`Text` / `At` / `Image` / `File` / `Reply`），分别产出 `{text}`、`{at}`、`{image, size}`、`{image, size}`、`{reply}`。
- 🧠 **会话记忆外部托管**：插件不做本地持久化，会话上下文由外部 PI AGENT 进程管理（`session_dir` 指定）。
- 🛠️ **工具调用闭环**：通过 `core.PIToolBackend` 把 QQ 侧能力（发消息 `send_message_to_QQ`、下载文件 `download_qq_file`、查消息 `query_qq_message_id`）注册为 pi 可调用的工具；后端配置经 `SHARE_STORE`（`PLUGIN_CONFIG`）注入。
- 🧩 **两级解析链**：`EventParseChain`（群/私聊事件元数据）与 `SegmentParseChain`（文本/AT/图片/文件/引用消息段）双链分发，`utils/easier_parser.parse_message` 一步合并产出完整消息结构（元数据 + message 段数组）喂给 agent。
- 🦆 **鸭子类型适配**：`adapters/EventAdapter` 不依赖具体 ncatbot 类型，通过属性探测兼容不同消息事件形态。
- 💾 **共享存储**：`stores/SHARE_STORE` 全局共享容器，键集中定义于 `consts/share_store_keys.py`（EVENT_PARSER / SEGMENT_PARSER / NCATBOT_API / PLUGIN_CONFIG / TOOL_BACKEND）。
- 🔧 **协议先行**：`protocols/` 定义 `Parser`、`ChainProtocol`、`StoreProtocol` 抽象（Parser 为鸭子类型协议），业务实现均依赖接口。
- 🧪 **本地测试**：`pytest/` 目录提供按模块划分的 pytest 用例（不随仓库提交），`utils.easier_parser`、解析链、适配器、工具组装均有覆盖。

## 架构设计

```
QQ / NapCat (OneBot)
        │ ncatbot 事件
        ▼
main.py  Claw(NcatBotPlugin)
        │ parse_message（easier_parser 合并 event + segment 两级解析）
        ▼
parsers/  EventParseChain → Group/PrivateMessageEventParser（事件元数据）
          SegmentParseChain → Text/At/Image/File/ReplySegmentParser（消息段）
        │ 统一 dict：{platform / from_group / created_at / group / sender / message: [...]}
        ▼
adapters/  EventAdapter（鸭子类型适配 ncatbot 事件：user_id / group_id / is_group / send）
        │
        ▼
core/PiClient.prompt() ────────────►  pi_bridge.PiClient ──►  pi Agent（LLM）
        │  isStreaming 时改走 steer() 注入                                 │ 工具调用
        │ 事件流（Text/ThinkingDelta, AgentSettled）                 ▼
utils/pi_event_classifier 分类 ◄───          core/PIToolBackend._execute_tool
        │                                              │
        ▼                                              ├─ tools/send_message.py   (send_message_to_QQ)
   发送到 QQ（easier_send）                            ├─ tools/download_file.py  (download_qq_file)
                                                       └─ tools/query_message_id.py (query_qq_message_id)
```

### 目录结构

```
miaoli_bot/
├── main.py                        # 插件入口：Claw，注册两级解析链与工具后端
├── manifest.toml                  # 插件清单（name/version/entry_class）
├── adapters/                      # ncatbot 事件鸭子类型适配器
│   ├── base_adapter.py            #   BaseAdapter 基类
│   └── event_adapter.py           #   EventAdapter（user_id/group_id/is_group/send）
├── chains/                        # 责任链实现
│   ├── base_chain.py              #   BaseParserChain：注册 + 分发给首个接受的 parser（短路）
│   ├── event_parse_chain.py       #   EventParseChain
│   └── segment_parse_chain.py     #   SegmentParseChain
├── consts/                        # 常量集中定义
│   └── share_store_keys.py        #   SHARE_STORE 键名（EVENT_PARSER/SEGMENT_PARSER/...）
├── core/                          # pi 桥接层
│   ├── pi_client.py               #   PiClient：prompt 流式接口，忙时按 streamingBehavior 走 steer/follow_up，出错落盘崩溃日志
│   └── pi_tool_backend.py         #   PIToolBackend：从 SHARE_STORE 读 host/port，记录工具调用
├── data/                          # 提示词资产（prompt_v1.0.md / prompt_v1.1.md）
├── enums/                         # 枚举定义
├── models/runtimes/               # 运行时数据模型
│   ├── dispatch_result.py         #   DispatchResult（链调度结果）
│   └── parse_result.py            #   ParseResult（parse_message 合并结果：event + segments）
├── parsers/                       # 解析器实现
│   ├── event_parsers/             #   Group/PrivateMessageEventParser
│   └── segment_parsers/           #   Text/At/Image/File/ReplySegmentParser
├── protocols/                     # 抽象协议：Parser / ChainProtocol / StoreProtocol
├── stores/                        # 全局共享存储（SHARE_STORE）
├── tools/                         # 暴露给 pi 的工具（发消息 / 下载 QQ 文件 / 查询消息）
├── pytest/                        # 本地 pytest 用例（gitignore，不提交）
└── utils/                         # 工具函数
    ├── easier_parser.py           #   parse_event / parse_segment / parse_message 快捷入口
    ├── easier_sender.py           #   private/group 便捷发送封装
    ├── event_ops.py               #   从事件取 id（群→group_id，私聊→user_id）
    └── pi_event_classifier.py     #   pi 事件分类（text/thinking 增量、agent 结束/错误）
```

## 数据流

1. QQ 消息经 NapCat → ncatbot → 触发 `Claw` 插件。
2. `on_message` 调用 `parse_message`：`EventParseChain` 解析事件元数据（群 → `GroupMessageEventParser`，私聊 → `PrivateMessageEventParser`），`SegmentParseChain` 逐段解析 `message`（文本 → `TextSegmentParser`，AT → `AtSegmentParser`，图片 → `ImageSegmentParser`，文件 → `FileSegmentParser`，引用 → `ReplySegmentParser`），合并为统一 dict（`platform`、`from_group`、`created_at`、`group`、`sender`、`message: [...]`）。
3. `PiClient.prompt(i_data, streamingBehavior="steer")` 将解析结果送入 pi Agent，流式返回事件；`prompt` 内部先 `get_state()` 判定，若 agent 正在输出则改走 `steer()` 注入新消息并直接返回（不产生事件流）。
4. `pi_event_classifier` 分类事件：正文增量实时回发 QQ；agent 结束即回复 `[DONE]` 并结束本轮；出错记录日志。
5. agent 需要调用工具时，经 `PIToolBackend` 执行 `send_message_to_QQ` / `download_qq_file` / `query_qq_message_id`，结果回流给 agent。

## 安装与使用

1. 将本目录放入 ncatbot 的插件目录（如 `plugins/miaoli_bot`）。
2. 确认运行环境已安装依赖：
   - `ncatbot`
   - `pi_bridge`（参见 [pi-bridge](https://github.com/lyt2011/pi-bridge)）
   - `aiofiles`
   - `pytest` / `pytest-asyncio`（仅本地跑测试需要）
3. 在 ncatbot 配置中为插件提供配置项（`core/PIToolBackend` 经 `SHARE_STORE` 的 `PLUGIN_CONFIG` 读取 `tool_backend_host` / `tool_backend_port`）。
4. 启动 bot，在 QQ 中私聊或群聊即可与 agent 对话。

### 本地测试

```bash
cd <插件父目录>          # plugins/
<venv>/bin/python -m pytest miaoli_bot/pytest/ -v
```

## 依赖

| 包 | 用途 |
|---|---|
| `ncatbot` | QQ 机器人框架 / 事件与消息 API |
| `pi_bridge` | pi 与 Python 的桥接层（`PiClient` / `PIToolBackend`，v0.5.4+） |
| `aiofiles` | 异步文件读写（崩溃日志落盘） |

> 注：`manifest.toml` 中 `pip_dependencies = []`，依赖需在运行环境中自行安装。

## 项目状态

v0.3.0 — 新增图片/文件/引用消息段解析与 `query_qq_message_id` 工具，插件配置入 `SHARE_STORE`，`PiClient.prompt` 忙时按 `streamingBehavior` 客户端侧分流（steer/follow_up）；单订阅者互斥（`asyncio.Lock` + 本地 `is_streaming`）列为 Future，仍在演进中。
