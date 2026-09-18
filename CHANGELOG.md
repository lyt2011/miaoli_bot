# Changelog

本项目所有重要变更均记录在此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循语义化版本（[SemVer](https://semver.org/lang/zh-CN/)）。

## [0.6.0] - 2026-09-18

### Added
- **插件配置化建会话（`config.yaml` + `main.py` `create_pi_factory`）**：新增插件目录 `config.yaml`，把原先写死在 `on_message` 里的建连参数（`session_dir="/tmp/"`、`data/prompt_v1.1.md`、`set_model("deepseek-official", "deepseek-flash")`）全部改为读配置 —— `session_dir`（默认 `/tmp/`）、`buffer_limit`（默认 `32 * 1024 * 1024`，配置文件未给该键时走默认值）、`prompt_file`（系统提示词文件路径，优先读文件）/ `pi_system_prompt`（内联回退，可为 `None`）、`default_provider` / `default_model`（`set_model` 的两个参数）。`create_pi_factory(session_id)` 返回无参异步工厂 `pi_factory`，`on_message` 仍以 `factory=…` 传给 `ensure_session`，工厂只在会话未命中时被调用
- **`protocols/closable.py` — `Closable` 运行时协议**：`@runtime_checkable` 的 `Protocol`，只声明 `async def close(self) -> None`，作为「实现 `close()` 的资源可被统一兜底清理」的结构化约定；`protocols/__init__` 导出
- **`main.py` `clean_share_store` — 兜底清理**：`on_close` 在显式关闭各组件之后，对 `SHARE_STORE` 做一次快照遍历（`keys()` / `values()` 配 `zip`），`isinstance(value, Closable)` 的逐个 `await value.close()`；非 `Closable` 记 warning 跳过，`close()` 抛错只记 warning 且不中断其余清理；close 之后 double-check `contains(key)`，仍在容器里就 `drop(key)`（对象已自行摘除则命中「不存在 但清理完成」的 warning 分支），逐键记 info 便于事后核对
- **`errors/miss_factory_error.py` — `MissFactoryError`**：`ensure_session` 未命中会话且未传 `factory` 时抛出（`errors/__init__` 导出）

### Changed
- **`PiSessionManager` 关闭方法更名为 `close()`**（`close_sessions` → `close`，`core/pi_session_manager.py` + `main.py._close_session_manager`）：与本次新增的 `Closable` 协议（`async def close`）同名，便于纳入通用兜底清理；**破坏性更名**，外部调用点需同步
- **`ensure_session` 签名调整**（`core/pi_session_manager.py`）：`create_timeout` 更名为 `timeout`（**破坏性更名**，默认值仍 `60.0`）；`factory` 由必填改为可选（`factory: PI_FACTORY = None`）并移到 `timeout` 之后，缺省且未命中时抛 `MissFactoryError`；命中缓存时不构造、不调用工厂
- **`_FACTORY_TYPE` → `PI_FACTORY`**：由 `Callable[[], Awaitable[PiClient]]` 改为 `Optional[Callable[[], Awaitable[PiClient]]]`，与「工厂可缺省」的新契约对齐
- **`on_close` 清理改走兜底路径**：`_close_session_manager()` 调用点注释掉（方法定义保留），改由 `clean_share_store()` 经 `Closable` 协议关闭 `PiSessionManager`
- **`protocols/parser.py` 的 `Parser` 加 `@runtime_checkable`**：与 `Closable` 对齐，允许运行时 `isinstance` 判定
- **建连日志收敛**：`ensure_session` 由「client 不存在 / 已存在 / 创建成功」三条 debug 收敛为进锁后一条 `{session_id} client 存在: True/False`；工厂协程先构造（`factory_coro = factory()`）再交给 `asyncio.wait_for(…, timeout=…)`，超时语义不变
- `main.py` 移除 `on_message` 中「私聊没法使用（需要 @）」的测试期 HACK 注释（`is_group and not event.message.is_at(…)` 的判定本身保留）

### Note
- **兜底清理不替代显式清理**：`clean_share_store` 只保证「把实现 `Closable` 的资源都 `close()` 过一遍」，`runtime_checkable` 的 `isinstance` 只判定属性名存在、不校验方法签名，也不保证被调对象真的幂等或可重复调用；失败路径只记 warning。`SHARE_STORE` 中未实现 `Closable` 的键（如 `NCATBOT_API` / `PLUGIN_CONFIG`）仍靠 `on_close` 里的显式 `drop`
- **`create_pi_factory` 未做配置校验**：`default_provider` / `default_model` 缺失会在建连时 `KeyError`（代码中已标 `NOTE | FIXME`，计划把配置换成 pydantic 动态模型），当前只是「临时可用」
- `prompt_file` 的读取发生在每次构造工厂时（每条消息一次读盘）
- **端到端手工验证**：主要功能（群 / 私聊对话、工具调用）与「关闭兜底清理」路径均已由作者在真实 QQ 环境验证通过

### Docs
- README 更新至 0.6.0：新增「配置化建会话」「兜底清理」特性，目录树补 `config.yaml` / `protocols/closable.py` / `errors/miss_factory_error.py` / `core/_prompt.py`，安装章节补配置项说明，`项目状态` 记录本次变更与遗留项
- 本地测试同步 `close_sessions` / `create_timeout` 更名，`PiSessionManager` 用例增至 18 例（新增 2 例 factory 缺省契约），全量 120 例通过（`tests/` 为本地用例、不随仓库提交）
- 补齐 `create_pi_factory` / `PiSessionManager`（`_pop_sessions` / `close` / `ensure_session`）/ `Closable` / `MissFactoryError` 的 docstring；修正内层 `pi_factory` 的返回值注解（原写作 `Callable[[], Awaitable[PiClient]]`，实际返回 `PiClient`）、`_Prompt` 的 `agen` 参数注解（`AsyncIterable` → `AsyncIterator`，实现依赖 `__anext__`）

### Future
- `core/_prompt.py`（本地 WIP，未接入 `PiClient`）：`_Prompt` 事件流包装（按事件类型注册回调、异常隔离、`aclose` / `async with` 收尾），落地 0.5.0 条目中「让 `prompt` 返回可遍历的 `Prompt` 对象并支持回调注册」的设想

## [0.5.4] - 2026-09-17

### Changed
- **`pi_bridge` 依赖下限提到 `>=0.6.0`**（`manifest.toml`）：0.6.0 为行为变更版本 —— `PiClient.prompt` 请求被拒时由「静默零事件」改为抛 `RequestRefuseError`，`PIProcess.build` 的关键字参数 `session` 更名为 `session_id`。本插件经 `PiClient.open(session_id=…, …)` 建连，不使用被更名的参数

### Note
- **本插件暂未捕获 `RequestRefuseError`**：PI 拒绝请求时异常会冒到 ncatbot 的事件处理器（日志可见 traceback，用户侧无回复）。待后续单独处理
- README 依赖表原先写作 `v0.5.4+`，与 `manifest.toml` 的 `>=0.5.5` 不一致，本次一并改为 `v0.6.0+`

## [0.5.3] - 2026-09-17

### Fixed
- **插件命令被当作普通对话、机器人重复回复**（`main.py`）：`on_message` 由默认优先级改为 `priority=-100`，让扩展插件先收到事件并自行决定是否截断。配合 `miaoli_like` 的 `赞我`（`priority=100` + `event.data._propagation_stopped = True`），该消息不再进入 LLM，消除「私聊发送 `赞我` 时本插件也回复一次」的重复响应

### Note
- 本插件的改动只是「最后处理」；截断本身由上游插件负责，上游不停传播则消息照常进入 LLM
- 已手动验证：`赞我` 由 `miaoli_like` 接手并回复，本插件不再处理该消息

## [0.5.2] - 2026-09-16

### Changed
- **`close_sessions` 关闭流程重构**（`core/pi_session_manager.py`）：把「取快照 + 清空缓存」下沉为同步方法 `_pop_sessions()`，`close_sessions` 只保留「幂等判定 → 置位 `_is_closing` → 取快照 → 逐个 `close()`」。`_pop_sessions` 是普通 `def` 而非 `async def`，因此「快照与清空之间不可能出现 await」由语言层面保证而非注释约定；幂等语义仍留在 `close_sessions`（`_is_closing` 为真时直接返回），对外行为与 0.5.1 完全一致

### Added
- 关闭语义补充两例（并发用例 14 → 16）：`test_close_without_sessions_is_safe`（空关闭不抛错且幂等，钉住「空快照被当作对象解包」这类回归）、`test_close_under_sustained_creation_leaves_nothing_open`（已缓存会话 + 20 个在建请求与关闭交错时，「快照关闭」与「在途回收」两条路径同时生效且不留未关闭 client）

### Note
- 快照方法 `_pop_sessions()` 只负责「把会话摘出来」，**不负责关闭** —— 它不知道摘出来的必须被 `close()`。目前仅 `close_sessions` 一个调用点，将来新增调用点时必须自行承担关闭责任
- `_locks` 字典按设计**不做清理**：per-session 锁的正确性依赖「同一 `session_id` 恒对应同一把 `Lock` 对象」，一旦在丢弃会话时删除条目，老等待者与新请求会持有两把不同的锁并同时进入临界区（实测：同一会话建出两个 client，其中一个被覆盖成无人引用的孤儿）。代价仅约 105 B/会话（1 万会话 ≈ 1 MiB），且 `main.py` 关闭时会 `SHARE_STORE.drop`，锁字典随 manager 实例一并回收

## [0.5.1] - 2026-09-16

### Added
- **`PiSessionManager` 高并发用例**（`tests/test_core_session_manager.py`，14 例）：同会话 50 并发只建一次、8 会话 × 25 并发互不串台、10 会话工厂 Barrier 汇合（不计时证明无全局锁）、慢会话不阻塞其他会话、200 任务交错负载、工厂超时 / 抛错后的缓存与锁状态、失败不被缓存（20 个等待者各自重试）、关闭幂等与并发关闭 exactly-once、关闭 vs 在途 / 排队请求的回收

### Changed
- **本地测试目录 `test/` → `tests/`**：`.gitignore` 忽略项与 README 中的目录树、测试命令同步更新（历史条目中的旧名保留）

### Fixed
- **关闭窗口期建出的 `PiClient` 未被回收（会话泄漏）**（`core/pi_session_manager.py`）：`ensure_session` 此前只在进锁前判一次 `_is_closing`，因此「已通过判定、随后阻塞在 per-session 锁上」或「已进入 `await asyncio.wait_for(factory(), …)`」的请求，会在 `close_sessions()` 完成之后才建连并写回 `self.sessions` —— 该 client 不在关闭快照内，永远不会被 `close()`。现改为在工厂返回后、写入缓存前再判一次 `_is_closing`（判定与写入之间无 await，对外原子），命中则 `await pi_client.close()` 回收已建出的 client 并抛 `SessionManagerClosingError`；进锁前的前置判定保留，作为「关闭后不再接单」的快速失败门槛
- 两个窗口均有用例钉住：`test_close_during_inflight_request_reclaims_created_client`（工厂窗口）、`test_close_during_queued_request_also_rejected`（排队窗口），xFail 标记随之摘除

### Note
- **关闭后仍在排队拿锁的请求**会各自白建一次 client 再回收（正确但不经济）；若要省掉这些白建，可再补一处「锁内二次判定」，或在 `close_sessions` 中跟踪并等待在途建连
- 用例覆盖的是并发不变量，与真实 PI 进程 / 网络环境下的并发行为不等价

### Docs
- README 更新至 0.5.1：`tests/` 路径同步，项目状态补充关闭窗口修复与高并发用例（全量 100 例通过）

## [0.5.0] - 2026-09-16

### Added
- **`core/pi_session_manager.py` — `PiSessionManager`**：按 `session_id` 管理 `PiClient` 生命周期。`ensure_session(session_id, *, factory, create_timeout=60.0)` 命中已有会话直接复用，未命中则在 per-session `asyncio.Lock`（`defaultdict(asyncio.Lock)`）内 `await asyncio.wait_for(factory(), timeout=create_timeout)` 建连并缓存（`factory` 为无参可调用对象，仅在未命中时惰性调用），避免同一会话被并发建出多个客户端；`close_sessions()` 以 `_is_closing` 标志幂等关闭，关闭时先原子替换 `self.sessions = {}` 再逐个 `await session.close()`，关闭期间新请求抛 `SessionManagerClosingError`
- **`errors/session_manager_closing_error.py`**：新增 `SessionManagerClosingError`（继承 `BaseBotError`），表示 SessionManager 正在关闭仍被请求创建会话；`errors/__init__` 导出
- **`consts/id_prefix.py`**：新增会话键前缀常量 `GROUP_PREFIX = "group-"` / `PRIVATE_PREFIX = "private-"`，`consts/__init__` 导出
- **`utils/sugar.py`**：新增 `concatenate_id(session_id, is_group=False) -> str`（群聊加 `group-`、私聊加 `private-` 前缀），`utils/__init__` 导出
- **`PI_SESSION_MANAGER` 共享键**（`consts/share_store_keys.py`）：值为 `"miaoli_bot/core.pi_session_manager"`，供全局定位会话管理器
- **`main.py` 新增 `_register_session_manager` / `_close_session_manager`**：在 `_share_store_lock` 保护下注册 / 取出并移除会话管理器（重复注册直接返回），关闭时调用 `close_sessions()`

### Changed
- **会话隔离落地：移除全局单例 `PiClient`**（`main.py`）：`on_load` 不再创建 `self.pi_client`（删除标注 `# HACK: 为了快速测试将使用全局单例 技术债` 的 `PiClient.open` / `set_model` 块），改为注册 `PiSessionManager`；`on_message` 构造 `session_id = concatenate_id(target_id, is_group=is_group)`，经本地 `_pi_factory`（`PiClient.open(session_id=…)` + `set_model("deepseek-official", "deepseek-flash")`）与 `session_manager.ensure_session(factory=_pi_factory, session_id=session_id)` 取得当前会话的 `PiClient` 后再 `prompt(...)`——不同群 / 私聊各自持有独立客户端与会话，互不串台
- **`main.py` `_close_tool_backend` 早退写法统一**：`return None` → `return`（与同文件其他早退分支一致）
- **建会话工厂改为惰性调用**：`main.py` 由 `ensure_session(factory=_pi_factory(), …)` 改为传可调用对象 `factory=_pi_factory`，`core/pi_session_manager.py` 内部由 `wait_for(factory, …)` 改为 `wait_for(factory(), …)`，工厂由 `ensure_session` 在未命中时调用，与 `_FACTORY_TYPE = Callable[[], Awaitable[PiClient]]` 标注一致
- 常量与导出对齐：`consts/__init__.py` / `core/__init__.py` / `errors/__init__.py` / `utils/__init__.py` 补齐新增符号与 `__all__` 条目

### Fixed
- **命中已有会话时不再构造无用协程**：调用点先求值 `_pi_factory()` 会在缓存命中时留下一个从未被 await 的协程对象（触发「coroutine … was never awaited」警告且白白构造 `PiClient.open` 调用栈），改为惰性调用后只在真正需要建连时才构造

### Note
- **SessionManager 并发稳定性未验证**：私聊与群聊的会话创建 / 正常对话已由作者手动验证通过（各会话独立、无串台），但 `PiSessionManager` 在高并发（同一 / 多会话同时 `ensure_session`、关闭与请求竞争）下的行为未做验证，也没有对应的自动化用例；涉及并发时序的场景需先用例验证后再依赖

### Docs
- README 更新至 0.5.0：新增「会话隔离」特性、`PiSessionManager` 架构与目录说明，数据流补充会话取用步骤（含工厂惰性调用语义），`项目状态` 补充本次变更与并发未验证说明

### Future
- **`PiClient.prompt` 返回可遍历的 `Prompt` 对象**：将 `prompt` 由「async generator + 调用方 `async for` 后写一串 `if is_agent_error / is_text_delta / is_thinking_delta / is_agent_end`」改为返回 `Prompt` 对象——该对象依旧可被遍历（`async for`），**遍历时行为与现行 `prompt` 逻辑完全一致**（含 `_stream_lock` 忙时分流到 `steer` / `follow_up`、异常日志与锁释放语义），同时提供事件回调注册入口（如 `on(event_type, callback)` / 通用 `add_callback`），由 `Prompt` 在事件到达时派发给已注册的回调。调用方（`main.py` 的 `on_message`）因此不再需要 `if`/`elif` 链与「未被处理的 event」兜底分支，把「事件 → 动作」的映射收敛为声明式注册；需一并定义回调异常隔离（单个回调抛错不影响事件流）、回调注册顺序与重复注册等语义

## [0.4.0] - 2026-09-16

### Added
- **新工具 `delete_qq_message`**（`tools/delete_message.py`）：按 `msg_id` 撤回（删除）对应的 QQ 消息，成功返回 `"successful"`；ncatbot api 不可用时返回 `"ncatbot api is unavailable"`；`tools/__init__` 导出并在 `main.py` 注册进 `PIToolBackend`
- **插件上下线日志**（`main.py`）：新增 `PLUGIN_NAME = "喵璃の本体"` 常量，`on_load` / `on_close` 分别记录「已加载 / 已卸载」info 日志

### Changed
- **未处理事件不再中断事件流**（`main.py` `on_message`）：原先在 `is_agent_end` 分支回完 `[DONE]` 后 `break` 退出事件循环，现改为循环自然走完，未匹配任何分支的 pi 事件记 warning 日志（`未被处理的 event -> <类型名>`），便于发现新事件类型
- **`utils/easier_sender.py` 移除 `*args` / `**kwargs` 透传**：`private_easier_send` / `group_easier_send` / `easier_send` 三个函数签名收紧为显式参数（`*args` / `**kwargs` 在内部并未使用）
- **本地测试目录改名 `pytest/` → `test/`**：`.gitignore` 忽略项同步更新，README 中的路径引用一并修正

### Docs
- README 更新至 0.4.0：工具列表与数据流补充 `delete_qq_message`，目录结构与本地测试命令同步为 `test/`

## [0.3.3] - 2026-09-15

### Added
- **`PiClient.is_streaming` 只读属性**（`core/pi_client.py`）：新增 `@property is_streaming -> bool`，直接返回 `self._stream_lock.locked()`，为外部提供不经过 RPC 的本地忙闲查询入口（此前外部若需判断需自行访问私有 `_stream_lock`）

### Changed
- **`main.py` 移除未使用的 `get_log` 导入**：`from ncatbot.utils import get_log` 在模块中无任何引用，删除以清理 lint 噪音（日志器实际由各模块自行 `get_log(...)` 获取）

## [0.3.2] - 2026-09-15

### Changed
- **插件入口类改名为 `MiaoLiBot`**：`main.py` 中的插件类 `Claw` 重命名为 `MiaoLiBot`（`main.py:48`），`manifest.toml` 的 `entry_class` 同步由 `"Claw"` 改为 `"MiaoLiBot"`；README 中相关引用一并更新

> **本次为纯改名，无 API 变动**：类重命名不改动任何公开方法签名、消息结构、工具接口或事件流语义，对已集成的调用方无影响，升级无需改动业务代码

### Fixed
- **消息段空值防护**（`main.py` `on_message`）：`parse_message` 调用前改用 `getattr(event, "message", None)` 取值并判空，缺失或为空时记录告警并提前 `return`，避免向 `parse_message(event, segments)` 传入 falsy 的 `segments`

## [0.3.1] - 2026-09-15

### Added
- **`errors/` 异常模块**：新增 `BaseBotError` 基类（`errors/base_bot_error.py`）与 `PIPromptBusyError`（`errors/pi_prompt_busy_error.py`），后者表示 pi 正在流式输出且 `prompt` 未指定 `streamingBehavior`；`errors/__init__` 统一导出
- **`PiClient._stream_lock`**（`core/pi_client.py`）：`__init__` 中初始化 `asyncio.Lock`，作为客户端侧单订阅者互斥的唯一依据

### Changed
- **`PiClient.prompt` 忙闲判定改为本地锁**（`core/pi_client.py`）：由原先「调用 `get_state()` → 读 `isStreaming`」的一次 RPC 往返，改为检查 `self._stream_lock.locked()`，与 `acquire()` 之间不再有 await 点，**消除 TOCTOU 时间窗口**——此前并发调用方可能同时读到 `isStreaming=False` 而各自订阅，无法原子保证 `_subscribers` 中只有一个活跃订阅者（0.3.0 列为 Future，本次落地）
- **`PiClient.prompt` 签名收紧**：由 `(*args, streamingBehavior=None, **kwargs)` 改为显式 `(message: str, *, images=None, streamingBehavior=None)`，与父类 `pi_bridge.PiClient.prompt` 对齐；`steer` / `follow_up` 调用同步改为显式关键字传参（`self.steer(message=message, images=images)`）
- **忙时未指定 `streamingBehavior` 由静默拒绝改为抛异常**：不再静默 `return`，改抛 `PIPromptBusyError`，使调用方能够区分「被 steer 掉」与「正常结束」（0.3.0 Future 中提出的待办）
- **异常日志覆盖率扩大**：`except ValueError` 改为 `except Exception` + `PI_LOGGER.exception()`。原写法在此路径上捕获率为零（`pi_bridge` 的 `prompt` 链路上不抛 `ValueError`，唯一的 `ValueError` 在 `open()` 建进程阶段，不经 `prompt`），且丢失 traceback
- **`manifest.toml` 移除 `aiofiles` 依赖**：`pip_dependencies` 收敛为 `{ ncatbot5 = ">=5.5.8", pi_bridge = ">=0.5.5" }`

### Removed
- **崩溃落盘逻辑**（`core/pi_client.py`）：删除 `except ValueError` 中的 32MB stdout 直读 + `aiofiles` 写 `/root/lastest_crash.log`（含路径拼写错误 `lastest`、`"w"` 覆盖模式、无 `try` 保护等缺陷）。该逻辑捕获率近零且转储失败会顶替原始异常，改由日志系统承接——`PI_LOGGER.exception()` 经 NcatBot 的 `TimedRotatingFileHandler` 自动落盘 `logs/bot.log`（按天轮转、默认保留 7 天），无需手动翻文件
- **`aiofiles` 依赖**：随崩溃落盘逻辑一并移除，`manifest.toml` / README 同步更新
- **无用 import**：`collections.deque`、`typing.List`、`aiofiles`

### Fixed
- **`PiClient` 实例化缺失**：`_stream_lock` 所需的 `__init__` 覆写此前不存在，新增后补齐 `super().__init__(*args, **kwargs)` 调用

### Docs
- README 更新至 0.3.1：忙时判定描述由 `get_state()`/`isStreaming` 改为本地 `asyncio.Lock`；目录结构补充 `errors/`；依赖表移除 `aiofiles`

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
- **提前终止时的锁释放时机**：`async for` 中途 `break` 时，async generator 的 `finally` 需经事件循环若干 tick 才执行，`_stream_lock` 的释放因此有短暂延迟。这是 Python async generator 的语言语义（`PiClient` 与父类同属一套机制，无法在子类内根治），调用方若需立即释放应显式 `await gen.aclose()` 或让 `async for` 自然耗尽。当前 `main.py` 在 `is_agent_end` 分支后的处理方式对该窗口的敏感度待评估

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

[0.5.2]: https://github.com/lyt2011/miaoli_bot/compare/d1863eb...main
[0.5.1]: https://github.com/lyt2011/miaoli_bot/compare/5b4140b...main
[0.5.0]: https://github.com/lyt2011/miaoli_bot/compare/50a3b2e...main
[0.4.0]: https://github.com/lyt2011/miaoli_bot/commit/50a3b2e
[0.3.3]: https://github.com/lyt2011/miaoli_bot/compare/f612505...main
[0.3.2]: https://github.com/lyt2011/miaoli_bot/compare/4ffdf61...f612505
[0.3.1]: https://github.com/lyt2011/miaoli_bot/compare/ebb8d53...4ffdf61
[0.3.0]: https://github.com/lyt2011/miaoli_bot/commit/ebb8d53
[0.2.0]: https://github.com/lyt2011/miaoli_bot/compare/e610876...55cb08f
[0.1.1]: https://github.com/lyt2011/miaoli_bot/compare/de11062...e610876
[0.1.0]: https://github.com/lyt2011/miaoli_bot/commit/de11062