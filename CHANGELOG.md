# Changelog

本项目所有重要变更均记录在此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循语义化版本（[SemVer](https://semver.org/lang/zh-CN/)）。

## [0.3.0] - 2026-09-14

### Added
- **消息段解析扩展**：新增 `ImageSegmentParser` / `FileSegmentParser` / `ReplySegmentParser`（`parsers/segment_parsers/`），图片/文件段产出 `{image, size}`、引用段产出 `{reply}`，`SegmentParseChain` 与 `parsers/__init__` 同步注册导出
- **新工具 `query_qq_message_id`**（`tools/query_message_id.py`）：按 `msg_id` 查询未经解析的 OB11 原始消息数据，返回 JSON 字符串；`tools/__init__` 导出并在 `main.py` 注册进 `PIToolBackend`
- **`PLUGIN_CONFIG` 共享键**（`consts/share_store_keys.py`）：ncatbot 插件配置加入 `SHARE_STORE`，`on_load` 写入、`on_close` 清理，供 `PIToolBackend` 等消费

### Changed
- **`PiClient.prompt` 重写忙时语义**（`core/pi_client.py`）：流式期间收到新消息不再依赖 prompt 内置 `streamingBehavior` 透传给 pi，而是 `get_state()` 判定 `isStreaming` 后由客户端提前分流——`steer` 走 `self.steer()`、`followUp` 走 `self.follow_up()`，随后直接 `return`，避免同一事件流被多个 Task 重复订阅；`main.py` 相应改为 `prompt(i_data, streamingBehavior="steer")`，删除调用侧原先手写的 `get_state` + `steer` 分支
- **`PIToolBackend.__init__` 改从 `SHARE_STORE` 取配置**（`core/pi_tool_backend.py`）：不再要求构造时显式传 `config`，改为 `SHARE_STORE.recall(PLUGIN_CONFIG, {})`，`main.py` 的 `_register_tools` 相应去掉 `self.config` 时序断言
- **`[DONE]` 兜底移动**：`main.py` 中 `event.reply("[DONE]")` 移入 `is_agent_end` 分支内，确保仅在正常结束时发送
- **`main.py` 过滤逻辑放宽**：移除测试期用户白名单，仅保留「群消息需 @」判定（私聊不再受 @ 限制），修复私聊无法使用的问题
- 崩溃日志读取缓冲由 32KB 提升至 32MB（`core/pi_client.py`）

### Docs
- README 更新至 0.3.0 架构（新增消息段/工具/共享键说明、目录结构与数据流同步）

### Future
- **单订阅者互斥（待实现）**：当前 `PiClient.prompt` 通过 `get_state()` 做流式判定属于一次 RPC 往返，存在 TOCTOU 时间窗口——并发调用方可能同时读到 `isStreaming=False` 而各自订阅，无法原子保证 `_subscribers` 中只有一个活跃订阅者。计划引入**本地 `asyncio.Lock`** 包裹「检查 → 置位 → 订阅 → 发指令」，并以本地 `is_streaming` 布尔标志（`False` 时置 `True` 正常开始，`True` 时直接跳过）替代实时状态查询，从而在客户端侧**严格保证单订阅者**。同时考虑将跳过路径由静默 `return` 改为 `raise`（或产出合成事件），以便调用方区分「被 steer 掉」与「正常结束」。

## [0.2.0] - 2026-09-13

### Added
- **message 正文解析接入主流程**：`main.py` 的 `on_message` 改由 `utils.easier_parser.parse_message(event, event.message)` 一步产出完整消息结构（`event` 元数据 + `segments` 段数组）喂给 agent（`55cb08f`）
- **`models/runtimes/parse_result.py`**：新增 `ParseResult`（frozen dataclass，即 `event` + `segments` 两个字段），`models/__init__` 与 `models/runtimes/__init__` 同步导出
- **本地 pytest 测试**：新增 `pytest/` 目录（`conftest.py` + 11 个 `test_*.py`，按模块划分，86 个用例全绿），并加入 `.gitignore` 不随仓库提交

### Changed
- **`utils/easier_parse.py` → `utils/easier_parser.py`**：改名并扩充为完整入口（`parse_event` / `parse_segment` / `parse_message` 三级快捷解析；`parse_message` 收集后一次性构造 `ParseResult`）
- **常量笔误修正**：`consts` 中 `SEGMENT_PARSE` → `SEGMENT_PARSER`（存储键值 `"miaoli_bot/chains.segment_parser"` 不变，仅变量名对齐）

### Fixed
- **`tools/send_message.py` 参数不匹配**：`easier_send` 调用改用当前签名（`chat_id` / `to_group` / `message`），修复运行期 `TypeError: missing 'chat_id'`
- **`created_at` 无法 JSON 序列化**：`parsers/event_parsers/*` 中 `created_at` 由 `datetime.now()` 改为 `datetime.now().isoformat(timespec="seconds")`（此前 `json.dumps` 直接抛 `TypeError: datetime not serializable`）

### Docs
- README 更新至 0.2.0 架构（Parser 命名、两级解析链、`parse_message` 数据流）

## [0.1.1] - 2026-09-13

> 重构中间态（WIP）版本：责任链节点全面改名，message 解析尚未接入主流程。

### Refactored
- **责任链节点抽象改名：Handler → Parser**（`protocols/handler.py` → `protocols/parser.py`，`BaseHandlerChain` → `BaseParserChain`）
- **`handlers/` → `parsers/`**：拆为 `event_parsers/`（`GroupMessageEventParser` / `PrivateMessageEventParser`）与 `segment_parsers/`（`TextSegmentParser` / `AtSegmentParser`）
- **单链拆双链**：`chains/event_chain.py` → `chains/event_parse_chain.py`，并新增 `chains/segment_parse_chain.py`（事件元数据 + 消息段两级解析）
- **提示词资产改名**：`data/prompt.md` → `data/prompt_v1.0.md`、`data/new_prompt.md` → `data/prompt_v1.1.md`
- **新增 `consts/share_store_keys.py`**：SHARE_STORE 键名（`EVENT_PARSER` / `SEGMENT_PARSER` / …）集中定义，消除散落魔法字符串
- 新增 `utils/easier_parse.py`（解析快捷入口雏形，0.2.0 完善为 `easier_parser.py`）

## [0.1.0] - 2026-09-12

### init
- **初始提交 `de11062`**：可用的核心链路（消息接入 → agent 对话 → 工具调用）
  - `main.py` 插件入口 `Claw`（`NcatBotPlugin`），注册解析链与工具后端
  - `chains/EventParseChain` 责任链 + `GroupMessageEventHandler` / `PrivateMessageEventHandler` 事件规整为统一 dict
  - `core/PiClient`（`pi_bridge` 桥接，prompt 流式接口，崩溃日志落盘）
  - `core/PIToolBackend`（配置文件驱动 host/port，工具注册与调用记录）
  - `tools/`：`send_message_to_QQ` / `download_qq_file`
  - `adapters/EventAdapter` 鸭子类型适配（不依赖具体 ncatbot 事件类型）
  - `utils/pi_event_classifier`：事件分类（text/thinking 增量、agent 结束/错误）；`utils/easier_sender`：便捷发送
  - `protocols/` 抽象契约（Handler / ChainProtocol / StoreProtocol）、`stores/SHARE_STORE` 全局共享存储（`asyncio.Lock` 保护）
  - 模型 `models/runtimes/DispatchResult`、`data/prompt.md` / `data/new_prompt.md` 猫娘人设、`manifest.toml` 插件清单

### Chore
- `3a9be1e`：`main.py` 添加 HACK 注释标记测试期技术债（白名单 / 非 @ 过滤 / 缓冲逻辑）
- `587d9ca`：`manifest.toml` 声明插件级 pip 依赖并带版本约束

[0.2.0]: https://github.com/lyt2011/miaoli_bot/compare/e610876...55cb08f
[0.1.1]: https://github.com/lyt2011/miaoli_bot/compare/de11062...e610876
[0.1.0]: https://github.com/lyt2011/miaoli_bot/commit/de11062