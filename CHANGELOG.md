# Changelog

本项目所有重要变更均记录在此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循语义化版本（[SemVer](https://semver.org/lang/zh-CN/)）。

## [0.9.1] - 2026-10-01

> 🔄 **meme 子系统的 sqlite 驱动由 `rapsqlite` 换成 `aiosqlite`**：`rapsqlite` 在 x86_64 上没有预编译轮子（要现场编译），而 `MemeSqlite` 用到的那点能力 `aiosqlite` 全都有 —— 取消该依赖，`manifest.toml` 的 `pip_dependencies` 由 10 项减到 9 项。

### Changed

- **`plugins/meme_extension/core/meme_sqlite.py`：`from rapsqlite import connect` → `import aiosqlite`**。两者建连时机不同 —— `rapsqlite.connect(path)` 是同步的，`aiosqlite.connect(path)` 必须 `await`，所以建连从 `__init__` 挪到 `async with` 的 `__aenter__`（在 DDL 之前）：`__init__` 只存 `self.path` 并声明 `self.conn: aiosqlite.Connection`。查询 / 写入接口（`query_tags` / `fetch_memes` / `fetch_meme_from_hash` / `is_hash_existing` / `insert_meme` / `remove_meme`）与调用方（五个工具统一 `async with MemeSqlite(...)`）均不变。
- **`manifest.toml`：移除 `rapsqlite = ">=0.5.1"`**；`aiosqlite` 保留（`SQLiteAdapter` 与 `MemeSqlite` 共用一份）。

### Note

- **验证**（真实 sqlite 文件，非静态核对）：跑通 `MemeSqlite` 全部接口 —— `__aenter__` 后 `conn` 确为 `aiosqlite.Connection`、建表（`memes` / `tags` / `sqlite_sequence`）与 `idx_tags_meme` 索引存在、`PRAGMA foreign_keys` 确实为开、插入与判重、`fetch_memes` / `fetch_meme_from_hash`（含未命中返回 `None`）、`query_tags` 单标签命中与多标签交集、按 hash 删除（返回 id）与重复删返回 `None`、级联清 tag 引用；再跨一次 `async with` 重开确认落盘。14 项断言全 PASS。
- **未验证**：`meme_extension` 子插件在 NcatBot 运行时下的工具端到端调用未跑（与 0.9.0 遗留的未验证项同一类）。

### Docs

- **README 更新至 0.9.1**：版本号 / 安装依赖列表（去掉 `rapsqlite`，并把 `aiosqlite` 的用途补上 `MemeSqlite`）/ 依赖表（删 `rapsqlite` 行，`aiosqlite` 行改为「`SQLiteAdapter` 与 `meme_extension.MemeSqlite` 共用」）/ 项目状态新增本版段
- **CHANGELOG 新增本条目**

## [0.9.0] - 2026-10-01

> 🔌 **`checkpointer` 真正接线（本次为架构级新增）**：`config.yaml` 的 `checkpointer.database` 现在能在 `memory` / `sqlite` / `postgresql` 之间切换，`main.py` 不再写死 `InMemorySaver()` —— 新增 `protocols/abc/checkpointer_adapter.py` 的适配器基类与 `adapters/check_pointers/` 的三个实现，把 `BaseCheckpointSaver` 的协议方法 1:1 转发给底层 saver。
>
> 📦 **内置子插件改为随仓库提交**：五个子插件由 `/sdcard/python/miaoli_bot_plugins` 迁入本仓库 `plugins/`。
>
> ⚠️ **配置键更名（破坏性）**：`check_pointer` → `checkpointer`，并新增 `extra` 键，`plugin_configs.miaoli_bot` 需同步调整。
>
> 🧹 **兜底清理机制删除（破坏性）**：`Closable` 协议与 `main.MiaoLiBot.clean_share_store()` 移除，资源释放回到显式 `close()`。

### Added

- **`protocols/abc/checkpointer_adapter.py`（新增）**：`BaseCheckpointerSaverAdapter(ABC, BaseCheckpointSaver)` —— memory / sqlite / postgresql 三类 checkpointer 的统一门面，逐个显式转发 19 个协议方法（`config_specs` / `get_next_version` / `with_allowlist` + `get_tuple` `list` `put` `put_writes` `delete_thread` `delete_for_runs` `copy_thread` `prune` + 8 个 `a*` 异步版本），另定义抽象 `connect(cls, connect_to, **kwargs)` 与 `close()`；同步转同步、异步转异步，inner 不支持哪一侧就照旧抛 `NotImplementedError`。`get` / `aget` 不转发（基类已实现为转调 `get_tuple` / `aget_tuple`），`get_delta_channel_history` / `aget_delta_channel_history` 也不转发（基类默认实现同样是走祖先链）。
- **`adapters/check_pointers/`（新增）**：`InMemoryAdapter`（`InMemorySaver`，无状态）、`SQLiteAdapter`（`aiosqlite.connect` + `AsyncSqliteSaver` + `setup()`，`close()` 关连接）、`PostgresqlAdapter`（`AsyncConnectionPool(open=False)` + `AsyncPostgresSaver` + `setup()`，`close()` 关池；`extra` 认 `max_size` / `min_size` / `autocommit` / `row_factory`），以及 `__init__.py` 导出。
- **`CheckPointerConfig.extra`（新增）**：`Dict[str, Any]`，默认 `{}`，透传给适配器的 `connect(**kwargs)`。
- **`plugins/`（新增，随仓库提交）**：`base_nodes` / `base_parsers` / `base_platform_tools` / `base_system_tools` / `meme_extension` 五个内置子插件（`plugin.toml` + 子插件自带 `config.yaml` 默认值）。
- **`manifest.toml` 依赖新增**：`langgraph-checkpoint-sqlite`（`>=3.1.1`）/ `langgraph-checkpoint-postgres`（`>=3.1.2`）/ `aiosqlite`（`>=0.22.1`）/ `psycopg`（`>=3.3.6`）/ `psycopg-pool`（`>=3.3.3`）。

### Changed

- **`main.py`**：新增 `CPA_MAPPING`（`database` → 适配器类）；`_build_graph(checkpointer)` 不再写死 `InMemorySaver()`；`on_load` 开头按 `plugin_config.checkpointer` 的 `database` / `connect_to` / `extra` 建连并注入图；`on_close` 改为 `await self.cpa.close()`（并移除 `clean_share_store()` 调用）。
- **`models/config/plugin.py`：`check_pointer` → `checkpointer`（破坏性）**，与 `main.py` 的取值统一。
- **`models/config/check_pointer.py`**：新增 `extra` 字段并补齐 `Any` / `Dict` 导入（原先注解用到未导入的名字，pydantic 会把模型标成 `not fully defined`，实例化即 `PydanticUserError`）。
- **`adapters/__init__.py` / `protocols/__init__.py` / `protocols/abc/__init__.py`**：导出表同步（新增 `BaseCheckpointerSaverAdapter` 与三个适配器，移除 `Closable`）。
- **`config.example.yaml`**：`sub_plugin.load_from` 更新为入仓后的 `plugins/` 目录；`checkpointer` 段落解注释并补充 `extra` 说明。
- **`.gitignore`**：新增 `!plugins/*/config.yaml` 例外（子插件默认值需要入库，根目录 `config.yaml` 仍忽略）。

### Removed

- **`protocols/runtime/closable.py`（`Closable` 协议）删除**：`protocols/runtime/__init__.py` 同步移除导出
- **`main.MiaoLiBot.clean_share_store()` 删除**：关闭流程不再做 `SHARE_STORE` 兜底遍历，改为显式 `drop` + `await self.cpa.close()`

### Fixed

- `InMemoryAdapter.connect` 首个形参写成 `self` 但内部用 `cls(...)`，作为 classmethod 会 `NameError`
- `SQLiteAdapter.connect` 的 `aiosqlite.connect(path)` 未 `await`：拿到的是未启动的连接代理，`setup()` 执行 SQL 时抛 `ValueError: Connection closed`
- `PostgresqlAdapter` 只暴露 `max_size` 而 `min_size` 固定为连接池默认值 4，`max_size < 4` 时抛 `ValueError: max_size must be greater or equal than min_size`（现在 `min_size` 收敛为 `min(kwargs.get("min_size", 4), max_size)` 并真正传入池）
- `BaseCheckpointerSaverAdapter.connect` 的 `@abstractmethod` / `@classmethod` 顺序（Python 3.14 下类定义阶段即 `AttributeError: attribute '__isabstractmethod__' of 'classmethod' objects is not writable`）

### Note

- **验证**（真环境 / 真库，非静态核对）：memory 与 sqlite 端到端跑通（同 thread 两轮续存 / `aget_state_history` / `close`）；postgresql 对 `127.0.0.1:15432/miaoli`（PostgreSQL 14.24）跑通 26 项断言 —— 建表与重复 `setup` 幂等、`checkpoints` / `checkpoint_writes` 真落行、`parent_config` 链完整、`adelete_thread` 后归零、`close()` 关池、同步路径抛 `asyncio.InvalidStateError` 并原样透传、`prune` / `copy_thread` / `delete_for_runs` 抛 `NotImplementedError`、`extra` 的 `max_size` / `min_size` / `row_factory` 确实落到连接池，跑完探针 thread 无残留。
- **未验证**：插件整体 `on_load` 未在 NcatBot 运行时跑过（本轮只到「`PluginConfig` 校验 → `CPA_MAPPING` 建连 → `MiaoLiBot._build_graph(adapter)` 能 `compile`」），五个子插件（`plugins/`）未做运行验证。
- **转发约束（后续改这个基类时别踩）**：协议方法必须逐个显式定义（基类自带同名空壳，`__getattr__` 转不到 inner）；签名必须与 `BaseCheckpointSaver` 逐字一致（Pregel 会用 `signature(checkpointer.aput_writes).parameters.get("task_path")` 内省，签名丢了 `task_path` 会被静默判定为「不支持」）；`with_allowlist` 必须重写（基类实现只换门面自己的 serde，inner 拿不到 allowlist）。

### Docs

- **README 更新至 0.9.0**：版本号 / 功能特性（新增 checkpointer 适配层，协议列表去 `Closable`，删除「关闭兜底清理」）/ 目录树（新增 `adapters/check_pointers/` 与 `plugins/`，`protocols/` 去 `Closable`）/ 数据流（`thread_id` 说明改为按 `database` 选实现，卸载流程改为显式 `close()`）/ 内置子插件章节（改为入仓 `plugins/` 并说明默认值入库）/ 安装依赖列表 / 配置表（`check_pointer` → `checkpointer`，补 `extra`，去掉「尚未接线」）/ 依赖表 / 项目状态新增本版段
- **`config.example.yaml` 与 `manifest.toml` 同步**，**CHANGELOG 新增本条目**

### Future

- **`PluginLoader` 收口**：消费 `SubPluginConfig.is_enable`；给 `load_from=None` 一个明确行为（跳过加载或抛清晰错误）；`load_from` 路径不存在时给可读报错而不是裸 `FileNotFoundError`
- **checkpointer 补完**：`sqlite` 侧 `extra` 目前无参数可配；`prune` / `copy_thread` / `delete_for_runs` 等线程管理能力待真正需要时再评估

## [0.8.3] - 2026-10-01

> 📦 **meme 子系统整体迁出主包**：`tools/` 与 `utils/meme_sqlite.py` 删除、`MemeConfig` 配置模型移除，meme 能力改由新增的内置子插件 `meme_extension` 提供；同时修复 0.8.2 遗留的 `CheckPointerConfig` 导入 `NameError` 与 `split_separator` 空串风险。

### Removed

- **`tools/` 整目录删除**（`tools/__init__.py` 与 `meme_ops/` 的 `send_meme.py` / `archive_meme.py` / `list_memes.py`）：主包不再内置任何工具，工具全部由子插件注册
- **`utils/meme_sqlite.py` 删除**：`utils/__init__.py` 同步移除 `MemeSqlite` 导出
- **`MemeConfig` 配置模型与 `meme` 配置键移除**（`config.yaml` 的 `meme:` 段一并删除）：0.8.2 待优化项里「计划随 `tools` 一起迁到独立子插件」的 TODO 落实

### Added

- **内置子插件 `meme_extension`（新增）**：承接迁出的 meme 子系统，自带 `config.yaml` 与 sqlite 存储，提供 `archive_meme` / `send_meme_to_qq` / `list_memes` / `remove_meme_by_hash` / `search_memes_by_tags` 五个工具（后两个为本轮新增）

### Changed

- **`core/graph_pipeline.py`：handler 排序改为按 `priority` 降序**（`reverse=True`，数值大者先执行）；配套 `base_nodes` 的注册优先级调整 —— `compact` 提到 `priority=1`（降序下先于 `call_llm` 执行，压缩在请求前生效）、`attach_image` 提到 `priority=10`（降序下先于 `invoke_tools` 执行）
- **`models/config/output.py`：`split_separator` 改为 `Optional[str]`（默认 `None`）**，空字符串仍被 `model_validator` 拒绝；`main.py` 增加 `None` 分支（不切块、整条发送），修复默认空串下 `str.split("")` 抛 `ValueError` 的问题
- **`models/config/plugin.py`：补齐 `CheckPointerConfig` 导入与字段**，修复 0.8.2 中「导入 `PluginConfig` 即抛 `NameError`」的问题

### Note

- 0.8.2 遗留问题里，「`CheckPointerConfig` 未接线导致的导入报错」与「`split_separator` 默认值风险」已处理；仍遗留：`PluginLoader` 不消费 `SubPluginConfig.is_enable`（无条件加载 `load_from` 下全部子插件）、`load_from` 为 `None` 时会在 `Path(None)` 抛 `TypeError`
- **未验证项**：本环境缺 `pydantic` / `ncatbot` 依赖，未做导入与真机运行验证；本次以静态核对（代码阅读 + 全量 `py_compile` 语法检查 + `git diff`）归纳

### Docs

- **README 更新至 0.8.3**：版本号 / 功能特性（去掉 meme 子系统、工具改由子插件注册）/ 目录树（去掉 `tools/` 与 `utils/meme_sqlite.py`）/ 内置子插件章节（补充 `meme_extension`）/ 配置表（去掉 `meme` 行、`split_separator` 说明更新）/ 依赖表 / 项目状态新增本版段
- **`config.example.yaml` 同步**：`output` 的「预留占位」注释更正为已落地消费，并补充 `sub_plugin` / `check_pointer` 示例
- **CHANGELOG 新增本条目**

### Future

- **`check_pointer` 真正接线**：把 `database` / `connect_to` 映射到 `InMemorySaver` / `AsyncSqliteSaver` / `AsyncPostgresSaver`，让 `config.yaml` 能动态切换 checkpoint 数据库（延续 0.8.2 的 Future）
- **子插件开关落地**：消费 `SubPluginConfig.is_enable`，并给 `load_from=None` 一个明确行为（跳过加载或抛清晰错误）

### 待优化项（项目内 HACK / TODO）

- **`main.py:171` `# HACK: 快速测试技术债 后续改成动态创建 (LLMManager)`**：`chat_model` 仍是每条消息 new 一个 `ChatOpenAI`，模型名 / `base_url` 硬编码，未接 `PluginConfig.providers`
- **`core/graph_pipeline.py:123` `# NOTE: 先不写错误处理`**：`_dispatch` 逐个执行 handler 时没有 try/except，任一 handler 抛错整轮请求即失败；「`GraphBubbleUp` 必须放行」的问题仍在
- **子插件侧 hack（`base_nodes/nodes/_compact.py`）**：`MAX_KEEP_MESSAGES` / `CONTEXT_WINDOW` 为测试期常量，未从配置读取

## [0.8.2] - 2026-10-01

> 🔌 **本次为插件化拆分（架构级变更）**：图节点、两级解析器与平台工具从主包移出，改由内置子插件在运行时注册；新增 `sub_plugin` 配置、`PluginLoader` 加载器与 `Registry` 注册门面，主包只保留图管线与加载框架。
>
> ⚠️ **配置键不向下兼容**：`account_config` / `meme_config` / `output_config` 更名为 `account` / `meme` / `output`，并新增 `check_pointer` 键，`plugin_configs.miaoli_bot` 需同步调整。
>
> 📦 **随附四个内置子插件**：`base_nodes` / `base_parsers` / `base_platform_tools` / `base_system_tools`（提交时一并带上）。

### Removed

- **`parsers/` 整个目录删除**（`parsers/__init__.py`、`event_parsers/`、`segment_parsers/`）：两级解析器改为子插件运行时注册，主包不再内置具体解析器
- **`core/nodes.py` 删除**：5 个图节点（`format_input` / `format_prompt` / `call_llm` / `on_tool_calling` / `last_msg_to_answer`）迁出，`core/__init__` 导出同步收敛为 `GraphPipeline` / `ToolRegistry` / `Registry` / `PluginLoader` / `registry`
- **`tools/` 下 5 个平台工具删除**（`send_message.py` / `send_file.py` / `download_file.py` / `query_message_id.py` / `delete_message.py`）：改由子插件注册；`tools/__init__` 只导出 `meme_ops` 的 `send_meme_to_qq` / `archive_meme` / `list_memes`
- **`models/plugin_config.py` 与 `models/runtimes/` 删除**：前者拆成 `models/config/` 包，后者更名为 `models/runtime/`（`models/__init__` 导入同步）
- **`protocols/` 旧四个平铺协议文件删除**（`chain.py` / `closable.py` / `parser.py` / `store.py`）：按「编译期抽象 / 运行时检查」拆成 `protocols/abc/` 与 `protocols/runtime/` 两个子包

### Added

- **`core/plugin_loader.py` — `PluginLoader`（子插件加载器）**：扫描配置目录下所有「带 `plugin.toml` 的直接子目录」，读 `enter_class` / `enter_file`（相对路径拼成绝对路径）→ 把子目录注册成 Python 包（`spec_from_file_location` + `submodule_search_locations`，让入口文件里的相对 import 能找到父包）→ 读可选 `config.yaml` 作为子插件配置 → 实例化入口类并 `await on_load()`；`unload()` 会 `on_close()` 并把整包从 `sys.modules` 抹掉（否则重载拿到的是旧模块对象，改了代码也不生效）；配套 `discover()` / `load_all()` / `unload_all()`
- **`core/registry.py` — `Registry`（子插件注册门面）**：`register_tool` / `register_segment_parser` / `register_event_parser` 直接写进 `SHARE_STORE` 的对应容器；另有 `on_agent_start` / `on_turn_start` / `on_before_request` / `on_request` / `on_after_request` / `on_tool_call` / `on_turn_end` / `on_agent_end` 八个事件钩子，按 `priority` 把节点注册进图管线；模块底部导出全局单例 `registry`
- **`core/tool_registry.py` — `ToolRegistry`**：以工具名为键的极简容器（`register` / `remove` / `tools` 属性），替代原先硬编码在 `main.py` 的 `TOOLS` 列表；配套新增 `consts.share_store_keys.TOOL_REGISTRY` 共享键
- **`protocols/abc/` — 编译期抽象层**：`PluginProtocol`（子插件基类：`__init__(config, registry)` + 抽象 `on_load` / `on_close`，本次新增）、`ChainProtocol`、`StoreProtocol`
- **`protocols/runtime/` — 运行时检查组**：`Parser` 与 `Closable` 两个 `@runtime_checkable` 协议（`isinstance` 判定用）
- **`models/config/` — 配置模型拆包**：`plugin.py`（`PluginConfig`）、`provider.py`（`Provider` / `LLM`）、`accounts.py`（`Accounts`，由原 `AccountConfig` 更名）、`output.py`（`OutputConfig`）、`sub_plugin.py`（`SubPluginConfig`）、`check_pointer.py`（`CheckPointerConfig`，**本次新增但尚未接线**，见 Note / Future）
- **`models/config/provider.py` — `LLM` 扩展**：在 `name` / `context_window` / `max_tokens` 之外新增 `visions`（`List[Literal["image", "video", "tool_calling", "text", "audio"]]`）与 `protocol`（`Literal["openai-completion", "openai-response"]`）两个字段（**尚无消费方**）
- **`models/config/check_pointer.py` — `CheckPointerConfig`**：`database ∈ {memory, sqlite, postgresql}`（默认 `memory`）+ `connect_to`（数据库地址）；`model_validator` 要求非 `memory` 模式必须提供 `connect_to`
- **`models/config/sub_plugin.py` — `SubPluginConfig`**：`is_enable`（默认 `false`）/ `load_from`（子插件目录）
- **`tools/meme_ops/` — meme 工具拆包**：`send_meme.py` / `archive_meme.py` / `list_memes.py`
- **`__init__.py` 顶层重导出**：`consts` 子模块、`GraphState` / `GraphRuntimeContext` / `SHARE_STORE`、三个返回值构造器（`custom` / `fail` / `success`）、四个协议（`PluginProtocol` / `StoreProtocol` / `ChainProtocol` / `Parser`），子插件可以用 `from miaoli_bot import ...` 一行拿到依赖
- **内置子插件四个**（本版随附，提交时一并带上；加载目录由 `sub_plugin.load_from` 指定）：
  - **`base_nodes`** — 图节点：`format_input` / `format_prompt` / `compact` / `call_llm` / `invoke_tools` / `attach_image` / `latest_to_answer`，在 `on_load` 里按事件与优先级注册进图管线；相比主包旧版新增**上下文压缩**（`_compact.py`：超窗时把历史压成一条 `<compaction>` 摘要、保留最近若干轮，`ToolMessage` 随所属轮次保留）与**图片附加**（`_attach_image.py`：把 `ToolMessage` 里的图片块挪成一条 `HumanMessage`，绕开工具消息不能携带多模态块的限制）
  - **`base_parsers`** — 两级解析器（群 / 私聊事件 + 文本 / AT / 图片 / 文件 / 引用消息段），注册进 `EVENT_PARSER` / `SEGMENT_PARSER`
  - **`base_platform_tools`** — 平台工具：`send_message_to_qq` / `send_file_to_qq` / `download_qq_file` / `query_qq_message_id` / `delete_qq_message`，注册进 `ToolRegistry`
  - **`base_system_tools`** — 系统工具：`bash` / `read_file` / `write` / `replace` / `read_image`，带自己的 `config.yaml`（`bash.limit` / `encoding` / `cwd` / `reader_timeout` / `bash_timeout`）与配置模型；`read_image` 依赖新增的 `filetype` 做类型嗅探
- **`manifest.toml` 依赖新增 `filetype = ">=1.2.0"`**（`base_system_tools.read_image` 用）

### Changed

- **`main.py` 大幅瘦身**：删掉 `_build_graph` 里的 5 处节点注册、`_register_event_parse_chain` / `_register_segment_parse_chain` 与 `store_lock`；`_build_graph` 改为静态方法，只负责 `wire()` + `compile(InMemorySaver())`；`on_load` 改为「建容器（`ToolRegistry` / 两级链 / 图）→ 起 `PluginLoader` 并 `load_all()`」，`on_close` 对称增加 `unload_all()` 与四个新键的显式 `drop`
- **群消息 @ 判定不再硬编码 QQ 号**：由写死的 `is_at("2449906317", …)` 改为读 `plugin_cfg.account.bot_id`
- **工具列表不再硬编码**：`context["tools"]` 由固定 `TOOLS` 常量改为 `tool_registry.tools`
- **输出切块与打字延迟落地**（原 `main.py` 里两条 `# TODO`）：按 `output.split_separator` 切分 `final_answer`、跳过空块，每块按 `len(块) * typing_speed ± typing_speed_offset` 随机 sleep 后再发送（此前 `OutputConfig` 三个字段无消费方）
- **配置键更名（破坏性）**：`account_config` → `account`（模型 `AccountConfig` → `Accounts`）、`meme_config` → `meme`、`output_config` → `output`（`config.example.yaml` 与 `config.yaml` 同步）
- **`models/graph_state.py` / `models/graph_runtime_context.py`**：导入路径对齐新包结构（`models.config` / `models.runtime`），另有一处空行与尾部换行整理
- **`consts/share_store_keys.py`**：新增 `TOOL_REGISTRY`，`consts/__init__` 导出同步
- **`errors/` 三个异常类统一格式**（补 `...`、docstring 收成一行，纯风格改动，无行为变化）
- **`data/prompts/prompt_v1.3.md` 微调**：明确「不喜欢用 markdown 标注信息」「系统能很方便地分句」，并补全若干句尾语气词

### Note

- **`CheckPointerConfig` 尚未接线**：模型已就位且 `PluginConfig` 引用了它，但 `models/config/plugin.py` 缺少对应 import，当前导入 `PluginConfig` 会抛 `NameError`；`main.py` 也仍写死 `InMemorySaver()`（修复与接入见 Future）
- **子插件加载的两个边界**：`SubPluginConfig.is_enable` 目前**只声明未消费**（`PluginLoader` 无条件加载 `load_from` 下的全部子插件）；`load_from` 为 `None` 时 `PluginLoader.__init__` 会在 `Path(None)` 处抛 `TypeError`
- **输出切块的默认值风险**：`output.split_separator` 默认是 `""`，而 `str.split("")` 会抛 `ValueError`，不配置该键时 `on_message` 最后一步会失败
- **未验证项**：本地 Python 环境缺依赖（`pydantic` / `ncatbot`），本次改动**未做导入与真机运行验证**，仅以静态阅读 + `git diff` 归纳

### Docs

- **README 更新至 0.8.2**：版本号 / 功能特性（子插件系统、工具闭环、输出切块与打字延迟）/ 架构图 / 目录树 / 新增「内置子插件」章节 / 配置表（新增 `check_pointer`、`output` 已落地消费、`sub_plugin` 说明）/ 依赖表（新增 `filetype`）/ 项目状态全部同步
- **CHANGELOG 新增本条目**，并按要求新增 `Future`（动态切换数据库 + `check_pointer` 适配器）与「待优化项」（项目内 `HACK` / `TODO` / `NOTE`）标注

### Future

- **让 `config.yaml` 动态切换数据库**：`check_pointer` 目前只有配置模型、没有消费方，`main.py` 仍写死 `InMemorySaver()`；计划由配置驱动 checkpoint 落库，让会话记忆可持久化、可换后端
- **新增 `check_pointer` 适配器**：为上一项配套 —— 在子插件体系里加一个 checkpointer 适配器（或在 `Registry` 上开注册口），把 `database` / `connect_to` 映射到具体 saver（`InMemorySaver` / `AsyncSqliteSaver` / `AsyncPostgresSaver`），避免主包直接依赖各后端驱动

### 待优化项（项目内 HACK / TODO）

- **`main.py:171` `# hack: 快速测试技术债 后续改成动态创建`**：`chat_model` 仍是每条消息 new 一个 `ChatOpenAI`，且模型名 / `base_url` 硬编码，未接 `PluginConfig.providers`（`Provider.models` / `LLM` 已定义 `context_window` / `max_tokens` / `visions` / `protocol`，但无人消费）
- **`models/config/plugin.py:12` `# TODO`**：`MemeConfig` 不属于 miaoli_bot 的原生配置，计划后续随 `tools` 一起迁到独立子插件
- **`core/graph_pipeline.py:123` `# NOTE: 先不写错误处理`**：`_dispatch` 逐个执行 handler 时没有 try/except，任一 handler 抛错整轮请求即失败；「`GraphBubbleUp` 必须放行」的问题仍在
- **子插件侧 `hack`（`base_nodes/nodes/_compact.py`）**：`MAX_KEEP_MESSAGES` / `CONTEXT_WINDOW` 为测试期常量（未从配置读取），token 估算也是「大致算一下」

## [0.8.1] - 2026-09-29

> ⚠️ **本版本含破坏性更名**：配置键 `meme_config.sqlite_path` → `db_path`、`send_file_to_qq` 的参数 `file` → `path`、`send_meme_to_qq` 的参数 `path` + `by` → `hash_`。旧 `config.yaml` 与既有调用写法需同步调整。
>
> ✅ **仍处优化态**：本次不含架构改动 —— 图管线 / 状态与上下文分离 / 分层配置 / 工具闭环四处骨架保持 0.8.0 定下的形态，改动集中在 meme 子系统从「未写完」落地为可用实现，以及工具层参数收口。

### Removed

- **`core/meme_manager.py` 删除**（`core/__init__` 的导入同步）：meme 子系统的数据访问整体改为 `utils/meme_sqlite.py` 的 `MemeSqlite`
- **`utils/meme_sqlite_ops.py` 删除**（`utils/__init__` 的导出同步）：连接与建表职责并入 `MemeSqlite`，由 `async with` 统一接管
- **`send_meme_to_qq` 去掉 `by` 参数与「按路径发图」分支**（**破坏性变更**）：原实现用 `path` + `by ∈ {file, hash}` 区分「本地文件」与「已归档的 hash」，但两个工具（`send_meme_to_qq` / `send_file_to_qq`）的参数表因此几乎同形，实测模型会选错工具；现只保留「按 hash 发已归档表情包」，「按路径发图」交给 `send_file_to_qq`

### Added

- **`utils/meme_sqlite.py` — `MemeSqlite`（`rapsqlite` 驱动，全异步）**：`__init__(path)` 建连接；`async with` 进入时按序执行 `PRAGMA foreign_keys = ON` 与三张 DDL（`memes` 表 / `tags` 表 / `idx_tags_meme` 索引），退出时 `commit` + `close`。查询接口：`query_tags(tags)`（按标签查，返回 `{meme_id: {description, base64, tags}}`）、`fetch_memes()`（列出全部 `(id, description, hash, base64)`）、`fetch_meme_from_hash(hash_)`（返回 `{id, description, hash, base64}`，未命中返回 `None`）、`is_hash_existing(hash_)`；写入接口：`insert_meme(tags, base64, description, hash_)`（一次事务写入表情包与去重后的标签）。三个私有方法（`_fetch_meme_ids_from_tags` / `_fetch_meme_infos_from_tags` / `_fetch_tags_from_meme_ids`）承担「标签 → id → 信息 → 标签」的三段查询
- **`list_memes` 落地**：该工具原先直接 `fail("工具未写完")`，现经 `MemeSqlite.fetch_memes()` 返回 `{meme_id: {hash, description}}` —— **不返回 base64**，让模型能列出可选表情包而不被图片体积撑爆上下文；未启用或未配置 meme 时仍统一返回 `fail("meme被禁用")`
- **`manifest.toml` 新增 `rapsqlite = ">=0.5.1"`**：meme 子系统的 sqlite 异步驱动，缺它会直接 `ModuleNotFoundError`
- **`utils/__init__.py` 导出 `MemeSqlite`**：工具层统一从 `..utils` 取用

### Changed

- **`MemeConfig` 的配置键 `sqlite_path` → `db_path`**（**破坏性变更**）：字段与校验器同步更名，`config.yaml` / 上层配置需改键；`MemeConfig` 未开 `extra="allow"`，键名写错会被 pydantic 静默丢弃，直到取 `meme_config.db_path` 时才 `AttributeError`
- **`tools/send_meme.py` 收敛为「只发已归档的表情包」**：参数由 `path` + `by` 变为 `hash_`，docstring 首句改为「发送一个**已归档的**表情包到 QQ」，未命中文案改为 `找不到 hash_ 为 <hash> 的表情包`
- **`tools/send_file.py` 的参数 `file` → `path`**（**破坏性变更**）：`get_size_MB(file)` 一并改为 `get_size_MB(path)`；`ToolSchema.path` 的类型由 `str` 收紧为 `FilePath`，路径不存在在**参数校验期**即被拒绝
- **`tools/archive_meme.py` 改走 `MemeSqlite`**：`async with` 内先 `is_hash_existing` 判重（命中即 `custom(False, message="该表情包已被归档", …)`），未命中才 `insert_meme`；返回体里的 `hash` 从查询结果取
- **`tools/query_message_id.py` 工具描述改写**：「查询 `message_id` 对应的 未经过特殊处理或解析的 OB11 协议信息」→「查询 `message_id` 对应的 QQ 消息」（对外描述里不再出现实现细节的协议名）
- **`models/plugin_config.py` 移除未使用的 `import os`**；`core/__init__.py` 调整导入顺序；`utils/__init__.py` 对齐缩进

### Fixed

- **`Image(url=…)` → `Image(file=…)`（`send_meme.py`）**：`ncatbot` 的 `Image` 模型字段是 `file` / `url` / `file_id` / `file_size` / `file_name`，其中 **`file` 必填**；只传 `url` 会让 pydantic 抛 `ValidationError: file: Field required`，异常被 `ToolNode` 包成 `status="error"` 的 `ToolMessage` 回给模型 —— 表现为「模型报怨工具坏了」，实则是这一行参数名写错
- **base64 两处类型错误（`send_meme.py`）**：`b64encode(...)` 与 sqlite 取出的 `base64` 都是 **bytes**，直接插进 `f"base64://{base64_data}"` 会拼成 `base64://b'/9j/…'`（`b'` 前缀污染载荷），两处均补 `.decode()`
- **`archive_meme` 解包 dict 拿到的是键名**：`meme_id, description, base64 = await fetch_meme_from_hash(…)` 对 dict 解包得到的是 `"id"` / `"description"` / `"base64"` 三个**字符串**（不报错、静默错值），改为先接住整个 dict 再按 key 取
- **`fetch_meme_from_hash` 返回值补 `hash` 键**：查询 SQL 只取了 `id, description, base64`，而调用方要读 `meme_info["hash"]` —— 补齐返回键，消除 `KeyError`
- **`MemeSqlite.__aexit__` 签名与关闭**：原先只声明 `(self)`，`async with` 退出时会以四个参数调用而抛 `TypeError`；同时补上缺失的 `await self.conn.close()`（原先只 `commit`，连接泄漏）
- **`is_hash_existing` 恒真**：原实现读 `cur.lastrowid`，而 `SELECT` 之后该值是 `-1`（`bool(-1)` 为 `True`）→ 改成读 `rows[0][0]`
- **`fetch_memes` 缺 `def`**：`async fetch_memes(...)` 是语法错误，插件整体无法导入
- **两处 SQL 语法错**：`memes` 建表语句最后一个字段后多一个逗号；`_fetch_tags_from_meme_ids` 的四段 SQL 字符串拼接缺空格（拼出 `'§')FROM tagsWHERE …`）
- **两处漏 import**：`utils/meme_sqlite.py` 的 `Tuple`（`fetch_memes` 返回值注解）、`tools/send_meme.py` 的 `Image`（取图那一行在用）
- **命名两处**：`_fetch_meme_ids_form_tags` → `_fetch_meme_ids_from_tags`（拼写）；`MemeSqlite` 三个方法的形参 `hash` → `hash_`（`hash` 遮蔽内建函数）—— 只改形参，SQL 列名与工具返回体里的 `hash` 键保持不变

### Note

- **meme 子系统的数据契约**：`memes(id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT NOT NULL, base64 TEXT NOT NULL UNIQUE, hash TEXT NOT NULL UNIQUE)` + `tags(tag TEXT NOT NULL CHECK (TRIM(tag) != ''), meme_id INTEGER NOT NULL, PRIMARY KEY (tag, meme_id), FOREIGN KEY (meme_id) REFERENCES memes(id))`；`base64` 实际以 **BLOB（bytes）** 落库（写入方给的是 `b64encode(...)` 的 bytes），读取方需 `.decode()`；`hash` = `md5(base64 文本)`，归档与查询两侧算法一致
- **验证方式（本地环境，非真机）**：`compileall` 报错数 0；pyflakes 全项目 0 条；导入链（`main` / `tools` / `core` / `utils`）正常；对真实库跑通 `MemeSqlite` 全部接口（建表 / 判重 / 查 hash / 列全部 / 按标签查 / 关连接重开数据仍在）；工具层用假 ncatbot api 端到端跑通 `send_meme_to_qq(hash_=…)` 与 `archive_meme` 的「已归档」分支
- **仍为占位或已知债**（沿用 0.8.0，本次未动）：`OutputConfig` 字段已定但无消费方；`main.py` 的 `chat_model` 仍是每条消息 new 一个 `ChatOpenAI`（标 `# HACK`）；`GraphPipeline._dispatch` 无错误处理（标 `# NOTE`，「`GraphBubbleUp` 必须放行」的问题仍在）；`_build_graph` 写 `SHARE_STORE` 未持 `store_lock`；`tests/` 里 0.7.0 时代的 147 例仍整体失效

### Docs

- **README 更新至 0.8.1**：版本号 / 工具描述（`send_meme_to_qq` 按 hash、`send_file_to_qq` 按 path）/ 目录树（`core/meme_manager.py` → `utils/meme_sqlite.py`）/ 配置表（`sqlite_path` → `db_path`）/ 依赖表（新增 `rapsqlite`）/ 项目状态全部同步
- **CHANGELOG 新增本条目**，并按「未实现的计划不留档」的约定移除 0.8.0 的 `Future` 段（该段原文 5 项本次均未实现）

## [0.8.0] - 2026-09-29

> ⚠️ **本版本为破坏性重构**：移除 `pi_bridge` 与外部 pi Agent 进程，改由插件内自建的 LangGraph 图管线驱动 LLM。依赖、配置结构、共享键、消息段字段全线变更，旧 `config.yaml` 与全局 `plugin_configs.miaoli_bot` 不能直接沿用。
>
> ✅ **重构已完成，项目自此进入优化态**：架构骨架（图管线 / 状态与上下文分离 / 分层配置 / 工具闭环）已经立住，后续以补齐功能、补错误处理、优化体验为主，不再是大改造。

### Removed

- **`pi_bridge` 依赖链整体移除**（**破坏性变更**）：删除 `core/pi_client.py`（`PiClient` 流式接口）、`core/pi_session_manager.py`（`PiSessionManager` 按 `session_id` 管理客户端）、`core/pi_tool_backend.py`（`PIToolBackend` 工具后端）、`core/_prompt.py`（`_Prompt` 事件流包装，0.6.0 起一直是未接入的 WIP）、`utils/pi_event_classifier.py`（pi 事件分类）、`errors/miss_factory_error.py`（`MissFactoryError`）、`errors/pi_prompt_busy_error.py`（`PIPromptBusyError`），`enums/` 目录一并清空删除。`manifest.toml` 的 `pip_dependencies` 由 `pi_bridge = ">=0.6.0"` 换成 `langgraph = ">=1.2.12"` + `langchain-openai = ">=1.6.6"`
- **`consts/share_store_keys.py` 删除 `TOOL_BACKEND` / `PI_SESSION_MANAGER`**：对应模块已不存在，共享容器不再持有这两类对象（`consts/__init__` 的导出同步移除）
- **`errors/` 删除两个异常类**：`MissFactoryError`（会话未命中且无工厂）与 `PIPromptBusyError`（pi 忙且未指定 `streamingBehavior`）—— 「建连工厂」与「事件流忙闲」两个概念随 pi 桥接层一起消失；`errors/session_manager_closing_error.py` 的 `SessionManagerClosingError` 保留（改由工具层复用）
- **提示词资产集中到 `data/prompts/`**：`data/prompt_v1.0.md` / `data/prompt_v1.1.md` 移入子目录，并补充 `prompt_v1.2.md` / `prompt_v1.3.md`，四个版本同处一地

### Added

- **`core/graph_pipeline.py` — `GraphPipeline`（158 行，本次重构的核心）**：把「事件 → 处理器」的编排从 `main.py` 抽成独立泛型类 `GraphPipeline[StateT, ContextT, InputT, OutputT]`（四个 TypeVar 取自 `langgraph.typing`）。`__init__(state_schema, context_schema=None, *, input_schema=None, output_schema=None)` 参数与 `StateGraph` 对齐；`register(event, node, priority=0)` 把处理函数登记为 `Handler` 并即时按 `priority` 排序（**同一事件可挂多个处理器**）；`wire()` 一次性产出 8 个节点 + 8 条边（含 `ON_AFTER_REQUEST` 经 `tools_condition` 分流到 `ON_TOOL_CALLING` / `ON_TURN_END` 的条件边）；`compile(checkpointer=…)` 返回 `CompiledStateGraph`；`ainvoke(input, thread_id, *, context)` 完成一次调用。**同事件多处理器的合并语义**：`_dispatch` 按优先级串行执行，把每个返回值当**增量**逐次合入，返回 `None` 视为「只读」跳过、返回 `dict` 视为「更新」；`_merge`（静态方法）借 `_graph.channels` 上各 channel 的 `operator`（如 `messages` 的 `add_messages`）做 reducer 合并，取不到 `operator` 的键直接赋值 —— 因此 `messages` 累加、普通键覆盖
- **`consts/graph.py` — 8 个图事件常量 + 2 个优先级边界**：`ON_AGENT_START` / `ON_TURN_START` / `ON_BEFORE_REQUEST` / `ON_REQUEST` / `ON_AFTER_REQUEST` / `ON_TOOL_CALLING` / `ON_TURN_END` / `ON_AGENT_END`（值形如 `miaoli_bot/graph.event.on_turn_start`）与 `MAX_PRIORITY = 200` / `MIN_PRIORITY = -200`，`consts/__init__` 全部导出。拓扑：`START → ON_AGENT_START → ON_TURN_START → ON_BEFORE_REQUEST → ON_REQUEST → ON_AFTER_REQUEST`，此后按有无 `tool_calls` 走 `ON_TOOL_CALLING → ON_BEFORE_REQUEST`（回到请求）或 `ON_TURN_END → ON_AGENT_END → END`
- **`core/nodes.py` — 5 个图节点**（文件头注明「先在这瞎写，后续换成自动发现」）：`format_input`（`ON_TURN_START`：把 `event` + `segments` 序列化成 JSON 文本包成 `HumanMessage` **追加**进 `messages`）、`format_prompt`（`ON_TURN_START`：用 `<account>` 标签块拼出管理员 / 机器人的 QQ 号与昵称，接上 `cfg.system_prompt` 写入 `system_prompt` 状态键）、`call_llm`（`ON_REQUEST`：`runtime.context["chat_model"].bind_tools(runtime.context["tools"])` 后以 `[SystemMessage(state["system_prompt"]), *state["messages"]]` 请求模型）、`on_tool_calling`（`ON_TOOL_CALLING`：`ToolNode(runtime.context["tools"]).ainvoke({"messages": …})`，`context` 无 `tools` 键时返回 `None` 跳过）、`last_msg_to_answer`（`ON_TURN_END`：取 `messages[-1]`，是 `AIMessage` 则写入 `final_answer`）
- **`models/graph_state.py` — `GraphState`**：`event` / `segments` / `messages`（`Annotated[list, add_messages]`，**唯一带 reducer 的键**）/ `final_answer` / `system_prompt` 五键。**静态人设不进 `messages`** —— `messages` 是「每轮追加通道」，`system_prompt` 走普通键（覆盖），否则每轮多留一份人设（实测第 3 轮人设出现 3 次）
- **`models/graph_runtime_context.py` — `GraphRuntimeContext`**：`plugin_config: PluginConfig` / `chat_model: BaseChatModel` / `tools: List[BaseTool]`。**LLM 客户端与工具列表走 `context` 不走图** —— `context` 不进 checkpoint、不做浅拷贝、结果保持原引用，放不可序列化对象（客户端、锁）才安全
- **`models/runtimes/handler.py` — `Handler`**：`@dataclass`，字段 `priority: int` + `function`，`GraphPipeline.register` 的登记单元
- **`models/plugin_config.py` 配置模型重构（**破坏性变更**）**：顶层由平铺的 `model_id` / `provider` 改为分层结构 —— 新增 `Provider`（`name` / `base_url` / `api_key` / `models: List[LLM]`）、`LLM`（`name` / `context_window` / `max_tokens`）、`AccountConfig`（`bot_id` / `root_id` / `bot_nickname` / `root_nickname`，**四项全必填**）、`MemeConfig`（`is_enable` / `sqlite_path` / `max_memes`，带「可以关闭+传路径，不能启用+不传路径」的 `model_validator`）、`OutputConfig`（**Future 占位**：`typing_speed` / `typing_speed_offset` / `split_separator`，字段先落地、消费方待实现）。`PluginConfig` 顶层变为 `providers` / `session_dir`（`DirectoryPath`）/ `prompt_file`（`FilePath`）/ `system_prompt` / `account_config`（**必填**）/ `meme_config` / `output_config`；`FilePath` / `DirectoryPath` 让路径在加载期就被校验。**`plugin_configs.miaoli_bot` 整块需按新结构重写**
- **`utils/tool_result_builder.py` — 工具返回值构造器**：`custom(status, **kwargs)` / `success(message)` / `fail(message)`，把工具的统一返回契约收敛成三个函数
- **`errors/api_unavailable_error.py` — `APIUnavailableError`**：api 不可用时在工具里抛出（`errors/__init__` 导出）
- **工具层由 4 个扩充到 8 个**：新增 `tools/send_meme.py`（`send_meme_to_qq`，`by` 参数决定 `meme` 是路径还是 uuid）、`tools/send_file.py`（`send_file_to_qq`，带 `get_size_MB` 体积判断）、`tools/list_memes.py`（`list_memes`，零参数工具直接用裸 `@tool`）、`tools/archive_meme.py`（`archive_meme`，`meme` 路径 + 非空 `tags`）；`tools/__init__` 导出 8 个，`main.py` 的 `TOOLS` 列表供 `bind_tools` 与 `ToolNode` 共用同一份
- **`config.example.yaml` 入版本控制**（**破坏性变更**）：`config.yaml` 由 `.gitignore` 排除（含密钥），仓库改以 `config.example.yaml` 作入库模板；模板按新的分层 schema 给全（`providers` + `prompt_file` + 必填的 `account_config`，`output_config` 以注释形式作占位），照模板 `cp` 出的配置可通过加载期校验
- **`consts/share_store_keys.py` 新增三键**：`PLUGIN_DIR`（`miaoli_bot/main_py_dir`）、`WORKSPACE_DIR`（`miaoli_bot/workspace_path`，ncatbot 分配的插件数据目录）、`GRAPH_PIPELINE`（`miaoli_bot/core.graph_pipeline`）

### Changed

- **`manifest.toml` 依赖声明**：`pip_dependencies` 改为 `ncatbot5 = ">=5.5.8"` + `langgraph = ">=1.2.12"` + `langchain-openai = ">=1.6.6"`
- **`main.py._build_graph` 接线**：`GraphPipeline(GraphState, context_schema=GraphRuntimeContext)` 后**显式**注册五个节点（`ON_TURN_START` × 2 = `format_input` + `format_prompt`、`ON_REQUEST` = `call_llm`、`ON_TOOL_CALLING` = `on_tool_calling`、`ON_TURN_END` = `last_msg_to_answer`），再 `wire()` + `compile(checkpointer=InMemorySaver())`，double-check 后存入 `SHARE_STORE` 的 `GRAPH_PIPELINE` 键。**「谁挂在哪个事件上」在 `main.py` 里一眼可见**（一个「装饰器自动发现」方案曾实现后被否决，理由是控制感不足）
- **`main.py.on_message` 改走图**：`parse_message` → `graph_pipeline.ainvoke({"event": …, "segments": …}, thread_id=session_id, context=…)` → `event_adapter.send(self.api, output["final_answer"])`；`context` 携带 `plugin_config` / `chat_model` / `tools`
- **`main.py.on_load` / `on_close` 共享键清单更新**：`on_load` 依次写入 `NCATBOT_API` / `PLUGIN_CONFIG` / `RAW_CONFIG` / `PLUGIN_DIR` / `WORKSPACE_DIR`，再建图、注册两级解析链；`on_close` 逐个 `drop` 六个键（原先的 `PI_SESSION_MANAGER` 换成 `GRAPH_PIPELINE`），最后 `clean_share_store()` 兜底
- **未使用导入清理**：`parsers/event_parsers/{group,private}_msg_parser.py` 去掉 `Optional`；`parsers/segment_parsers/{image,reply,file}_parser.py` 去掉重复的 `Any` 与未用的 `Optional`
- **`utils/__init__.py` 导出表重排**：移除 `pi_event_classifier` 的四个分类函数（`is_agent_end` / `is_agent_error` / `is_thinking_delta` / `is_text_delta`），改导出 `tool_result_builder` 的 `custom` / `fail` / `success`
- **`models/__init__.py`** 新增导出 `Handler` / `GraphRuntimeContext` / `GraphState`

### Fixed

- **`parsers/segment_parsers/file_parser.py` 返回值键名改对**（**破坏性变更**）：`{"image": data.url or data.file, "size": data.file_size}` → `{"file": …}` —— 原来文件段和图片段返回同一个 `image` 键，下游无法区分
- **三处漏 import 的注解补齐**：`models/plugin_config.py` 的 `Union`（`OutputConfig` 用 `Union[int, float]` 但只导入了 `Optional, Self, List`）、`main.py` 与 `models/graph_runtime_context.py` 的 `List`。三者都不报 `NameError`，详见 Note

### Note

- **本次为重构收尾**：下面各项都是优化态下的改进点（架构本身已成立），不阻塞使用与后续迭代。
- **Python 3.14 的注解延迟求值（PEP 649）把「漏 import 类型」从「立刻 `NameError`」变成了「静默失效」**：`main.py` 的模块级注解 `TOOLS: List[BaseTool]` 与 `models/graph_runtime_context.py` 的 `TypedDict` 注解都没人解析，漏 `List` 也能正常 import、运行无感；**只有 pydantic 这种必须解析注解来建 schema 的使用方才炸** —— `OutputConfig` 漏 `Union` 会让 `PluginConfig.model_validate()` 抛 `PydanticUserError: 'PluginConfig' is not fully defined; you should define 'Union', then call 'PluginConfig.model_rebuild()'`，而这一句正是 `on_load` 的第一行，**插件直接加载不上**。已修复；`Union[int, float]` 也可直接写成 `float`（pydantic 本身会把 `int` 收成 `float`），保留 `Union` 是为了不动原写法
- **`OutputConfig` 是预留占位**：字段已定、类型校验正常，但当前没有消费方 —— `main.py` 里对应位置留着 `# TODO: 添加\n\n分割` / `# TODO: 添加打字时间延迟`，落地计划见 Future
- **`main.py` 的 `chat_model` 是临时实现**：`on_message` 里每条消息 new 一个 `ChatOpenAI(model="deepseek-flash", base_url="https://api.deepseek.com/v1", api_key=self.cfg.providers[0].api_key)`，代码标了 `# HACK: 快速测试技术债 后续改成动态创建`；供应商 / 模型的选择尚未接 `PluginConfig.providers`
- **`GraphPipeline._dispatch` 暂无错误处理**（代码标 `# NOTE: 先不写错误处理`）：某处理器的异常会直接冒到 `ainvoke` 调用方；后续需注意 `GraphBubbleUp` 必须放行（`except Exception` 会吞掉 `interrupt` —— `GraphInterrupt` 的 MRO 是 `GraphInterrupt → GraphBubbleUp → Exception`）
- **`GraphPipeline.compile()` 不返回 app**：`_app` 由 `compile` 写入实例自身，`main.py` 不接返回值；`_build_graph` 的写入路径（`SHARE_STORE.contains` 判定 → 建 → `compile` → double-check 后 `SHARE_STORE.set`）**未持 `self.store_lock`**，与 `_register_*_parse_chain` 的整段持锁风格不一致
- **旧测试全量失效**：0.7.0 记录的 147 例本地 pytest 用例（`PiSessionManager` / `_Prompt` / `PluginConfig` 等）针对的是 pi 桥接层，随本次重构整体作废，待重写

### Docs

- **README 更新至 0.8.0**：标题 / 简介 / 版本号改写为「LangGraph 自建图管线」，功能特性、架构图、目录结构、数据流、配置表、依赖表、项目状态全部按重构后的状态重写；`pi_bridge` 相关描述（`PiClient` / `PiSessionManager` / `PIToolBackend` / 流式事件分类 / `RequestRefuseError` 未捕获）整体删除
- CHANGELOG 新增本条目

## [0.7.0] - 2026-09-18

### Added
- **`models/plugin_config.py` —— `PluginConfig`（pydantic v2 配置模型）**：把插件配置从「裸 dict + 各处 `get` 取键」升级为声明式模型。字段：`model_id`（`str`，必填）、`provider`（`str`，必填）、`session_dir`（`str`，默认 `tempfile.gettempdir()`）、`system_prompt`（`Optional[str]`）、`prompt_file`（`Optional[str]`）；`model_config = ConfigDict(extra="allow")` 保留未声明的额外键（`buffer_limit` / `tool_backend_host` / `tool_backend_port` 仍可属性访问）；`@model_validator(mode="after")` 中 `prompt_file` 优先 —— 读文件（UTF-8）覆盖 `system_prompt`，验证器始终 `return self`（不触发 pydantic 的「返回值非 self」告警）。`models/__init__` 导出 `PluginConfig`
- **`RAW_CONFIG` 共享键常量**（`consts/share_store_keys.py`）：`"miaoli_bot/ncatbot.plugin.config"`（即原 `PLUGIN_CONFIG` 的字符串值），用于存放 ncatbot 合并后的原始配置 dict；`consts/__init__` 一并导出
- **`main.MiaoLiBot.cfg`**：`__init__` 中声明为 `Optional[PluginConfig] = None`，`on_load` 开头由 `PluginConfig.model_validate(self.config)` 赋值，供 `create_pi_factory` 及后续模块按属性取配置

### Changed
- **配置键名对齐模型字段**（`config.yaml` + `main.py`）：`default_model` → `model_id`、`default_provider` → `provider`、`pi_system_prompt` → `system_prompt`（`session_dir` / `prompt_file` 键名不变）；`config.yaml` 同步为 `model_id: "deepseek-flash"` / `provider: "deepseek-official"` / `session_dir: "/tmp/"` / `prompt_file: data/prompt_v1.1.md`。**破坏性变更**：全局 `plugin_configs.miaoli_bot` 中的旧键名不再生效
- **`PLUGIN_CONFIG` 共享键的值由原始 dict 改为 `PluginConfig` 实例**（`main.py`）：`on_load` 中 `SHARE_STORE.set(PLUGIN_CONFIG, self.cfg)`，ncatbot 合并后的原始 dict 改存新增的 `RAW_CONFIG` 键；`on_close` 对两个键都显式 `drop`（`clean_share_store()` 兜底清理保持不变）
- **`create_pi_factory` 改从 `self.cfg` 取配置**（`main.py`）：`session_dir` / `buffer_limit` / `system_prompt` / `provider` / `model_id` 全部 `getattr(self.cfg, …)`（`buffer_limit` 带 32 MiB 兜底 —— 它是 extra 键、不是模型字段）；删除「配置缺失会在建连时 `KeyError`」的 `NOTE | FIXME` 技术债与随之而来的临时实现
- **`PIToolBackend` 改按属性读配置**（`core/pi_tool_backend.py`）：`config.get("tool_backend_host")` → `getattr(config, "tool_backend_host", None)`（port 同理），`SHARE_STORE.recall` 的默认值改用哨兵 `object()`；键名打错会响亮报错，而不是静默回落环境变量默认值
- **提示词读盘时机前移**：`prompt_file` 的读取从「每次构造工厂（≈每条消息一次读盘）」改为「插件加载时一次」（`on_load` 的 `model_validate` 内），`create_pi_factory` 直接复用 `self.cfg.system_prompt`
- **`on_close` 恢复显式 `_close_session_manager()` 调用**：先前实测兜底清理时注释掉的显式关闭改回常态，`clean_share_store()` 仍作为最后一道防线

### Fixed
- 修正 `create_pi_factory` 中 `getattr(self.cfg, "model")` 的字段名笔误（字段实为 `model_id`）—— 该写法会被 `getattr` 的默认值静默吞掉，向 `set_model` 传入 `model_id=None`

### Note
- **配置校验前移到加载期（fail-fast）**：`on_load` 第一行即 `PluginConfig.model_validate(self.config)`，必填项缺失 / 类型不符会在插件加载时抛 `ValidationError`；ncatbot 的 `load_plugin` 会捕获并记 error 日志，**只让本插件加载失败，不会拖崩 bot**（不再等到首条消息才 `KeyError`）
- `buffer_limit` / `tool_backend_host` / `tool_backend_port` 仍是 extra 键（保留在 `model_extra` 中、`model_dump()` 会一并输出），**没有类型校验与默认值保护**，取值方需自带兜底
- 配置只在加载期解析一次：运行期经 `set_config()` / `update_config()` 改动配置**不会刷新 `self.cfg`**，需重新加载插件
- `prompt_file` 指向不存在的文件会抛 `FileNotFoundError`（非 `ValueError`，pydantic 不包装成 `ValidationError`）；`prompt_file` 为空字符串时会命中 `Path("").read_text()` 的 `IsADirectoryError`
- **端到端手工验证**：群 / 私聊对话、工具调用、兜底清理路径均由作者在真实 QQ 环境验证通过

### Docs
- README 更新至 0.7.0：特性「配置化建会话」改写为配置模型语义，架构图 / 目录树（新增 `models/plugin_config.py`）/ 数据流第 3、7 步 / 配置表（改为模型字段名并补 `RAW_CONFIG` 与 fail-fast 说明）/ 共享键清单 / `项目状态` 全部同步
- `create_pi_factory` docstring 同步为模型字段名
- 本地测试 147 例通过：`PluginConfig` 用例 27 例（必填契约 / `session_dir` 默认与覆盖 / `prompt_file` 优先级与 UTF-8 / extra 语义与未知属性 / 与真实 `config.yaml` 的字段对齐守卫 / `PLUGIN_CONFIG` 接线与 `PIToolBackend` 取值回归），合计 `PiSessionManager` 18 例、`_Prompt` 16 例、其余原有用例不变（`tests/` 为本地用例、不随仓库提交）

### Future
- `buffer_limit` 是否升级为模型字段（当前靠 `extra="allow"` 承载，缺类型校验与统一默认值）
- 运行期配置热更新：`set_config()` 后重新解析 `self.cfg`（现在必须重载插件）
- `core/_prompt.py`（本地 WIP，未接入 `PiClient`）与 `RequestRefuseError` 未捕获两项遗留不变

## [0.6.0] - 2026-09-18

### Added
- **插件配置化建会话（`config.yaml` + `main.py` `create_pi_factory`）**：新增插件目录 `config.yaml`，把原先写死在 `on_message` 里的建连参数（`session_dir="/tmp/"`、`data/prompt_v1.1.md`、`set_model("deepseek-official", "deepseek-flash")`）全部改为读配置 —— `session_dir`（默认 `/tmp/`）、`buffer_limit`（默认 `32 * 1024 * 1024`，配置文件未给该键时走默认值）、`prompt_file`（系统提示词文件路径，优先读文件）/ `pi_system_prompt`（内联回退，可为 `None`）、`default_provider` / `default_model`（`set_model` 的两个参数）。`create_pi_factory(session_id)` 返回无参异步工厂 `pi_factory`，`on_message` 仍以 `factory=…` 传给 `ensure_session`，工厂只在会话未命中时被调用
- **`protocols/closable.py` — `Closable` 运行时协议**：`@runtime_checkable` 的 `Protocol`，只声明 `async def close(self) -> None`，作为「实现 `close()` 的资源可被统一兜底清理」的结构化约定；`protocols/__init__` 导出
- **`main.py` `clean_share_store` — 兜底清理**：`on_close` 在显式关闭各组件之后，对 `SHARE_STORE` 做一次快照遍历（`keys()` / `values()` 配 `zip`），`isinstance(value, Closable)` 的逐个 `await value.close()`；非 `Closable` 记 warning 跳过，`close()` 抛错只记 warning 且不中断其余清理；close 之后 double-check `contains(key)`，仍在容器里就 `drop(key)`（对象已自行摘除则命中「不存在 但清理完成」的 warning 分支），逐键记 info 便于事后核对
- **`errors/miss_factory_error.py` — `MissFactoryError`**：`ensure_session` 未命中会话且未传 `factory` 时抛出，异常携带 `session_id` 属性（消息为「`<session_id>` 工厂缺失」）便于定位到具体会话（`errors/__init__` 导出）

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