# Changelog

本项目所有重要变更均记录在此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循语义化版本（[SemVer](https://semver.org/lang/zh-CN/)）。

## [0.13.0] - 2026-10-06

> 🖼️ **工具附件修复从 `base_nodes` 拆出、独立成子插件 `tool_attachment_fixer`（破坏性）**。`base_nodes/nodes/_attach_image.py` 整个删除 —— 它把所有模型都当作「不接受 `tool` 消息带多模态块」来处理、只扫末尾连续的一段 `ToolMessage`、且只挑 `image` / `image_url` 两种块（其余模态**静默丢弃**，实测确认 `audio` 块会消失）。新子插件把这三点全部改掉：按 `models` 名单门控、扫全表、整个 content 列表原样搬运。
>
> ⚠️ **破坏性**：`base_nodes` 不再提供工具附件改写，升级后需自行加载 `tool_attachment_fixer`，否则工具结果里的多模态块会原样进上下文（对不接受这种形状的模型将直接 `400`）。

### Added

- **`plugins/tool_attachment_fixer/`（新子插件，入口类 `ToolAttachmentFixer`）**：工具附件修复。`fix_tool_attachment` 节点挂在 `ON_TOOL_CALLING`（`priority=NORMAL-2`），把**非字符串**的 `ToolMessage.content` 整体挪进紧跟其后的一条 `HumanMessage`（`id=f"image-{tool_call_id}"`），原 `ToolMessage` 正文换成配置里的 `replace_text`，返回 `Overwrite` 整表替换；无改动时（`is_changed == False`）返回 `None`，不写任何增量。
  - **配置**（`config.yaml`）：`enable` / `models`（生效的模型名单，`<provider>/<model>` 与 `<model>` 两种写法都认，命中任一即生效；**留空 = 对所有模型生效**）/ `replace_text`（替换后 `ToolMessage` 的正文）
  - **`utils/guards.py`**：判据函数 `is_target_model` / `is_tool_message` / `is_block_content` / `is_target_message`（依赖方向单向 `nodes → utils → consts`）；`__init__.py` 只导出节点消费的两个（`is_target_model` / `is_target_message`）
  - **自带 `README.md`**：含配置说明与「与 `base_nodes` 的关系」（说明本节点由 `attach_image` 移植而来、两处不可同时启用），**12 个子插件全部有 README**

### Changed

- **`base_nodes` 的 `attach_image` → `tool_attachment_fixer` 的 `fix_tool_attachment`，四处行为有意差异**：① **模型门控** —— 只对 `models` 里声明的模型生效（旧节点对所有模型无条件改写）；② **扫描全表**而非只扫末尾连续的一段 `ToolMessage`（旧节点依赖「附件只可能出现在本轮最后一条消息」的隐含前提，历史里有旧残留时永远修不到，而那类残留恰恰每轮 `400`）；③ **搬运整个 content 列表**而非只挑图片（旧节点的 `_pick_images` 只认 `type in ("image", "image_url")`，`audio` 等其余模态块**静默丢弃**，实测确认）；④ **原地改 `content`** 而非新建 `ToolMessage` 逐字段复制。新建 `HumanMessage` 的 `id` 由 `f"images-{tc1}-{tc2}"`（多条合并成一条）改为 `f"image-{tool_call_id}"`（一个 `ToolMessage` 配一条）
- **`ON_TOOL_CALLING` 优先级链收窄**：`invoke_tools(0) → attach_image(-1) → 默认跳转(-9999)` → `invoke_tools(0) → fix_tool_attachment(-2) → 默认跳转(-9999)`
- **两处陈旧注释修正**（纯注释，行为未变）：`base_nodes/nodes/call_llm.py` 的「压缩后的摘要已由 `compact` 写进 messages」→ `context_compactor`（`compact` 已不在 `base_nodes`）；`pending_tool_fixer/main.py` 的「优先级高于 `compact(1)` 与 `call_llm(0)`」→ 去掉 `compact(1)`（该节点现在是 `ON_BEFORE_REQUEST` 的 `NORMAL`，与本节点不在同一事件上，`(1)` 还是 0.12.0 前的旧值）

### Removed

- **`plugins/base_nodes/nodes/_attach_image.py` 整个删除**（119 行，含 `_pick_images` / `_pick_text` 两个私有辅助函数与 `DEFAULT_NOTICE` / `IMAGE_PREFIX` 两个常量）
- **`base_nodes` 的 `attach_image` 注册与导入导出**：`main.py` 的 `self.registry.on_tool_call(attach_image, priority=NORMAL-1)` 与 `from .nodes import attach_image`、`nodes/__init__.py` 的 `from ._attach_image import attach_image` 与 `__all__` 条目全部移除
- **`base_nodes/README.md` 的 `attach_image` 与 `compact` 两行表格**：`compact` 那行是 0.12.0 拆出 `context_compactor` 时漏改的遗留（源码已无该节点），本次一并删掉，连同「`compact` 必须排在 `call_llm` 之前」那句排序说明

### Fixed

- 🔴 **`tool_attachment_fixer` 的 5 处缺导入**（插件在开发期修复，一并记录）：`nodes/fix_attachment.py` 缺 `SHARE_STORE` / `PLUGIN_CONFIG` / `ToolMessage` / `HumanMessage` / `Overwrite` —— 前两个会 `NameError`，后三个会让节点静默失效；同时补上节点所依赖的 `consts/PLUGIN_CONFIG` 键（`main.py` 的 `on_load` / `on_close` 相应 `set` / `drop`）
- 🔴 **`models/plugin_config.py` 缺 `from typing import List`**：服务器 Python 3.12 在 `def` 时立即求值注解，漏导入会 import 即 `NameError`
- 🔴 **节点读错 state 键名**：`state.get("provider", "null")` / `state.get("model", "null")` 读的两个键在 `GraphState` 里都不存在（真名是 `provider_name` / `model_name`，由 `main.py` 写入）—— 实测门控恒拿到 `"null"`、`models` 非空时永远不命中，**整个节点等于没装**；修正后实测命中模型返回 `Overwrite`、未命中返回 `None`

### Note

- **`isinstance(content, list)` 等价于「非字符串」**：`ToolMessage` 会把 `dict` / `None` / `int` / `bool` 等非 list 输入全部 coerce 成 `str`（实测 `None → 'None'`、`123 → '123'`、`True → 'True'`、裸 `dict → "{'type': 'text', …}"`），所以 `.content` 只可能是 `str` 或 `list` 两种，判据无需再单独写 `not isinstance(content, str)`
- **判据名从 `is_vision_block` 改为 `is_block_content`**：该函数只看「是不是块列表」、**不检查有没有图片**，`vision` 一词会误导（旧 `attach_image` 里叫这个名字是因为它真的只挑图片块）
- **空 `list` 也会被迁移**：`content=[]` 属「非字符串」，会产出 `HumanMessage(content=[])`（一条正文为空的消息）—— 按「非 str 全部迁移」的口径这是预期行为（工具返回空列表也在内），未做特判

### Future

- **`base_nodes/README.md` 的 `compact` 表格行已于本版删除**，但同类「文档滞后于代码」的遗留可能还有 —— 子插件表与 README 的对应关系尚未有自动化校验
- **`tool_attachment_fixer` 的 `models` 门控依赖 `state` 里的 `provider_name` / `model_name`**：这两个键是 `UntrackedValue`（单次 `ainvoke` 内可见），若将来在**跨轮**场景下读它们会拿到 `None` → 门控退化为不命中

## [0.12.0] - 2026-10-05

> 🧠 **上下文压缩从 `base_nodes` 拆出、独立成子插件 `context_compactor`；`GraphState` 里「每轮用完即丢」的 6 个键改用 `UntrackedValue`（破坏性）**。`base_nodes/nodes/_compact.py` 整个删除 —— 它把 `CONTEXT_WINDOW = 128000` 写死在代码里（原注释即标 `# HACK`）、token 用「字符数求和」粗估、提示词与保留条数都是模块级常量。新子插件把这些全部配置化（`keep_count` / `prompt_file` / `calculate.mode`），并**读模型真实配置**判断阈值（`usage + max_tokens >= context_window` 才压，为输出预留空间）。同时把 `GraphState` 的 `event` / `segments` / `provider_name` / `model_name` / `final_answer` / `system_prompt` 六个键从普通键改为 `Annotated[T, UntrackedValue]` —— 它们只在**单次 `ainvoke` 内**可见，**不再写入 checkpoint**（`channel_values` 现在只剩 `messages`）。
>
> ⚠️ **破坏性**：① `base_nodes` 不再提供上下文压缩，升级后需自行加载 `context_compactor`，否则长对话不再自动压缩；② `GraphState` 这 6 个键不再跨轮持久化 —— 子插件若在**后续轮次**读它们将读到 `None`（同一次 `ainvoke` 内跨事件读仍正常，实测 `system_prompt` 可跨 3 个以上事件传到 `call_llm`）；③ `manifest.toml` 新增 `pillow` / `tiktoken` 两个硬依赖。

### Added

- **`plugins/context_compactor/`（新子插件，入口类 `ContextCompactor`）**：上下文压缩。`compact` 节点挂在 `ON_BEFORE_REQUEST`（`priority=NORMAL`），流程为「算 token → 比阈值 → 压 → 整体替换」：阈值判断是 `usage_tokens + max_tokens < context_window` 时不压、直接返回 `None`（不写任何增量）；压缩请求体为 `[SystemMessage(system_prompt), *messages, HumanMessage(prompt)]`（无 `system_prompt` 时省略）；最后返回 `{"messages": Overwrite([HumanMessage("<compaction>摘要</compaction>"), *最近 keep_count 条])}`。
  - **配置化**（`config.yaml`）：`enable` / `encoding` / `prompt_file`（绝对路径）/ `keep_count` / `calculate.mode`（`base` 或 `tiktoken`）/ `calculate.encoder`（`o200k_base` / `cl100k_base`，`mode=tiktoken` 时必填，由 `CalculateConfig` 的 `model_validator` 校验）
  - **提示词可编辑**：`data/compact_prompt.md`（懒加载，`encoding` 指定编码）
  - **utils 四个模块**：`image_ops.py`（`b64_to_image` / `image_to_tokens`）/ `block_ops.py`（`HOLDER` + `handle_block` / `handle_dict_block` / `handle_str_block`）/ `sugar.py`（`keep_recent_messages` / `merge_contents`）/ `easier_calculate.py`（`base_calculate` / `tiktoken_calculate`），依赖方向单向 `easier_calculate → sugar → block_ops → image_ops`
  - **保留规则**：`keep_recent_messages` 从后往前收，只对 `HumanMessage` / `AIMessage` / `SystemMessage` 计数，**`ToolMessage` 不占配额**，避免把「有请求没返回」的 `tool_calls` 切开
- **`manifest.toml` 新增两个依赖**：`pillow`（`>=12.3.0`，图片宽高解析）与 `tiktoken`（`>=0.14.0`，精确 token 计数；此前是直接 import 但未声明，靠 `langchain-openai` 的传递依赖混进来）—— `pillow` 是本版新引入，`tiktoken` 是补声明
- **7 份子插件 `README.md`**：`account_injector` / `base_nodes` / `base_parsers` / `base_platform_tools` / `base_topology` / `orphan_tool_fixer` / `pending_tool_fixer` —— 加上原有的 `base_system_tools` / `meme_extension` / `tool_permission_manager` 与新插件，**11 个子插件全部有 README**
- **`GraphState` 引入 `UntrackedValue`**（`from langgraph.channels import UntrackedValue`）：`event` / `segments` / `provider_name` / `model_name` / `final_answer` / `system_prompt` 六键改为 `Annotated[T, UntrackedValue]`，`messages` 保持 `add_messages` 不变

### Changed

- **`GraphState` 的 6 个键不再落盘（破坏性）**：实测改造前 `channel_values` 含 7 个键，改造后**只剩 `['messages']`**；20 轮真实对话的 checkpoint 存储量**省 34%**。`UntrackedValue` 与 `EphemeralValue` 的区别是「不落盘」vs「落盘但下一步清空」，后者是 langgraph 内部件（`START` 通道、扇入屏障），对「要跨 3 个以上事件存活」的 `system_prompt` 不适用
- **`main.py` 的 `final_answer` 取值改 `.get()` 兜底**：`answer_string = (raw_output or {}).get("final_answer")` + `if answer_string is None: self.logger.warning(...); return`。两个原因 —— ① `UntrackedValue` 不落盘，本轮没走到 `on_agent_end` 时该键**不存在**（原来直接下标会 `KeyError`）；② `ainvoke` 在**无任何通道值时返回 `None`**（实测），原来的 `output[...]` 会当场崩
- **顺带修掉一个真 bug（陈旧读）**：改造前不写的轮次会把**上一轮的旧值**带回（实测第 1 轮读到 `'第一轮的答案'`、第 2/3 轮键不存在），改造后行为一致
- **`node_connection_fix` → `base_topology`**：0.11.0 的提交信息里写的是旧名，本次改名落地（目录、`plugin.toml`、入口类、两处 `SHARE_STORE` 键字符串、`config.yaml` 路径同步）
- **`orphan_tool_fixer` / `pending_tool_fixer` 的注册事件从 `on_before_request` 移到 `on_request`**（优先级相应改为 `NORMAL+2`），与 `compact` 分开事件
- **`base_calculate` 公式修正**：`len(contents)` → `int(len(contents) * 0.7)`。原式相当于 1 token/字，实测真实语料约 0.55 tok/字（消息里大量 JSON 事件体）、纯中文约 0.9，于是触发点被推到 96% 以上、几乎没有余量；新系数在真实语料下触发时占用约 76%（留 24% 余量）。返回类型同时从 `float` 修正为 `int`（原与 `-> int` 注解不符）

### Removed

- **`plugins/base_nodes/nodes/_compact.py` 整个删除**（含 `MAX_KEEP_MESSAGES = 5` / `CONTEXT_WINDOW = 128000` / `COMPACT_MESSAGE` / `_last_common_idx`）
- **`base_nodes` 的 `compact` 注册与导入**：`main.py` 的 `self.registry.on_request(compact, priority=NORMAL+1)` 与 `from .nodes import compact`、`nodes/__init__.py` 的 `from ._compact import compact` 与 `__all__` 条目全部移除。改后全图 `compact` 节点数由 **2 个降为 1 个**（原来新旧两套压缩同时注册，新的先跑并压缩、老的再跑时字符数已小于是恒返回 `None`，属死重）

### Fixed

- 🔴 **`context_compactor` 的 6 处必崩**（插件在开发期修复，一并记录）：① `PrivateAttr(default=None, description=...)` → `TypeError`（`PrivateAttr` 签名只有 `default` / `default_factory` / `init`）；② `Field(default=CalculateConfig)` → **实例共享**（实测改一个另一个跟着变），改 `default_factory`；③ `easier_calculate.py` 的 `encoding.encode(contents, ...)` 里 `contents` 从未定义 → `NameError`；④ 入口类没继承 `PluginProtocol` → 实例化 `TypeError`；⑤ `main.py` 的 `if plugin_cfg.enable: return None` **逻辑反了**（`enable: true` 时永不注册）；⑥ `nodes/compact.py` 读 `state["provider"]` 而该键不存在（应为 `provider_name`）
- 🔴 **`context_compactor/utils/sugar.py` 的 `except <???>:` 语法错误**：`<???>` 不是合法异常名（`od` 确认字节即 `3c 3f 3f 3f 3e`），`import` 即 `SyntaxError`；改为 `except Exception:`（内置名，无需导入）
- 🔴 **`image_to_tokens` 的两处必崩**：`image.weight`（拼写错误，应为 `image.width` → `AttributeError`）与 `image_b64.split(",")[-1]` **缺赋值**（`data:` 前缀没剥掉 → `b64decode` 抛 `binascii.Error`）
- 🔴 **`context_compactor` 的 5 个文件缺导入 + 1 个空导出**：`models/plugin_config.py` 缺 `PrivateAttr`，`utils/sugar.py` 缺 `Any` / `List` / `AIMessage` / `HumanMessage` / `SystemMessage`（3 个文件共 8 个缺失名字），`utils/easier_calculate.py` 缺 `Any` / `List`，`nodes/compact.py` 与 `main.py` 则整套缺失；`nodes/__init__.py` 为空、`compact` 未导出。**服务器是 Python 3.12（注解在 `def` 时立即求值）**，漏导入的类型名会直接 `NameError`，不像本地 3.14 那样延迟到使用时才炸
- **`prompt` 属性的返回类型撒谎**：注解写 `-> str` 但 `prompt_file` 为 `None` 时实际返回 `None`，改为 `Optional[str]`

### Note

- **图片 token 估算的实测依据**：`image_to_tokens` 用 `int(sqrt(min(宽,1920) × min(高,1080)))` 折算占位符个数，占位符取汉字 `图` —— 它在 `o200k_base` 里**严格 1 字符 = 1 token**（可打印 ASCII 全部会被 BPE 合并，实测 `'a'×1000 → 125 token`、`' '×1000 → 9 token`；`\0` 也会 2 字符并成 1 token）。实测 DeepSeek 真实图片成本是 **216（起步，≤512×512）→ 1026（封顶）**，本估算给 32 → 1440，偏差在 **2.4 倍以内**且方向偏保守
- **摘要提示词对照实验**（真实数据 `private-3640942712`，497 条消息，生产温度，每组 5 次）：**A（无 system_prompt + 第三人称）0/5 错；B（带 system_prompt + 第三人称）0/5 错；C（带 system_prompt + 第一人称）2/5 错**。出错的变量是「第一人称」而非「带 system_prompt」，且 B 的事实覆盖率最高 —— 因此仓库默认提示词用**第三人称**。C 的具体错误：把「一千米跑 3 分 19 秒」与「拼车回罗定」混成一个事实、把 10 月 4 日写成 8 月 4 日
- **`prompt_file` 用绝对路径**：不再依赖进程 CWD（原相对路径要求 CWD 恰为仓库父目录，否则 `ValidationError: Path does not point to a file`）。服务器部署时路径不同，需单独改或加进 rsync 排除名单
- **验证**（真跑）：① 全仓 `compileall` rc=0；② `ruff --select F401,F811,F821,F841` 全仓只剩 `main.py:153` 一处既有 F841；③ 全量插件加载 **11/11**，`ON_BEFORE_REQUEST` 处理器为 `pick_tools(1) → compact(0) → 默认跳转(-9999)`；④ `compact` 节点实跑 —— 低于阈值返回 `None`、超阈值返回 `Overwrite` 6 条（1 摘要 + 5 保留）；⑤ `image_to_tokens` 真 PNG 全链路（64×64→64、1024×1024→1024、3000×2000→1440，`min()` 归一化生效），空 url → `0`、坏图 → `1000`；⑥ 边界 7 组（纯字符串列表 / 无 `data:` 前缀 / 空 url / 缺 `image_url` / 未知模态 / 缺 `type` / 嵌套 list）全部不崩；⑦ `on_close` 的 `drop` 生效（`recall` 抛 `KeyError`）；⑧ **服务器 Python 3.12** 独立验证 import 与数值一致；⑨ `manifest.toml` 经 `tomllib` 解析通过
- **未验证**：NcatBot 运行时下的端到端对话仍未跑；本版只在真实插件 + 真实 config + 假模型下验证，未真实调用 LLM 端点；`context_compactor` 的 tiktoken 模式**未在服务器上验证**（服务器连不上 `openaipublic.blob.core.windows.net`，编码文件下不下来，故 `config.yaml` 默认 `mode: base`）

### Future

- 🐛 **`system_prompt` 通道的覆盖问题（已知 Bug，待重新设计）**：`GraphState.system_prompt` 是**普通键**（无 reducer → last-write-wins），于是**多个子插件往同一通道注入时，后写的会静默覆盖先写的** —— 实测 `NORMAL+1` 的注入者内容被 `NORMAL` 的注入者整个吞掉。但这个键当初写成普通键是有原因的：它需要「每轮重置、跨轮不累积」，而单纯的 concat 通道（`operator.add`）会让片段逐轮累加（实测 3 轮后 `'AAA'`）。**两条需求相互冲突** —— 多插件共存要求「追加」，跨轮干净要求「重置」，因此必须「concat 通道 + 每轮用 `Overwrite` 重置」两件事一起做（已实测该组合可行：3 个片段全在、顺序稳定、跨轮不累积；重置节点须挂最高优先级 `MAXIMUM`，且必须用 `Overwrite` 而非直接写值，否则仍会被 reducer 当成追加）。**当前未落地，方案与实测数据见开发记录**；触发条件是「有第二个子插件需要注入提示词」，现在只有一个注入者（`account_injector`），暂无实际影响。
- 🐛 **坏图片会让压缩一并失败（自锁）**：`compact` 与 `call_llm` 都发送全量 `messages`，若其中含 API 拒绝的图片（截断 PNG、非图片字节等），两侧会**同时 `400`** —— 压缩自救的路被堵死，坏图片留在 checkpoint 里导致每轮都失败。API 确实会拒绝（`400 unsupported image`），且 `read_image` 的类型白名单只看 magic number（**仅 8 字节的 PNG 头也能通过 `filetype.guess`**）。方向：写一个插件在请求前验证并替换坏图片块，而不是在 `read_image` 里塞 `PIL.open`（会把「图片语义」耦合进「文件读取」）。

## [0.11.0] - 2026-10-04

> 🔌 **补上 0.10.0 留下的缺口：新增 `base_topology` 子插件，图重新可端到端跑通**。0.10.0 把 `wire()` 改成 edgeless 之后，`tools_condition` 条件边随之一并删除，「下一个事件是谁」改由处理器主动返回跳转指令决定 —— 但当时**没有任何处理器负责这件事**，于是图跑完 `ON_REQUEST` 就静默结束、`final_answer` 缺失、`main.py` 当场 `KeyError`。本版补上的 `base_topology` 就是那个「默认跳转」：**一个事件一个节点文件**（`nodes/on_agent_start.py` / `on_turn_start.py` / … / `on_agent_end.py`），每个节点只返回一条 `Goto`，把旧 `wire()` 的 8 条静态边与那条条件边**原样搬到插件层**（`ON_AFTER_REQUEST` 该去 `ON_TOOL_CALLING` 还是 `ON_TURN_END` 的分支判断由节点里的 `is_tool_calling(messages)` 承担）。它注册在**最低优先级** `MINIMUM`，因此任何子插件挂在任何更高档位都能抢在默认跳转之前改道或叫停 —— **框架不定义顺序，默认顺序由插件声明，且随时可被覆盖**。
>
> ⚠️ **本次是破坏性变更**：优先级常量从 `EARLIEST`(200) / `LATEST`(-200) / `NORMAL`(0) **三档改为九档等比阶梯** —— `MAXIMUM`(9999) / `HIGHEST`(1000) / `HIGH`(100) / `MEDIUM`(10) / `NORMAL`(0) / `LOW`(-10) / `LOWEST`(-100) / `TRIVIAL`(-1000) / `MINIMUM`(-9999)。`EARLIEST` 与 `LATEST` **两个名字已不存在**，任何引用它们的子插件会 `ImportError`。改等比阶梯的理由是插件里已经在用 `NORMAL+1` / `NORMAL+2` / `NORMAL+3` 这类微调，档间差 10 倍才能保证这些微调不跨档（如 `MEDIUM+3`=13 仍 < `HIGH`=100）。

### Added

- **`plugins/base_topology/`（新子插件，入口类 `BaseTopology`）**：edgeless 拓扑下的**默认跳转**，把 0.10.0 删掉的 8 条静态边与 1 条条件边在插件层复原。目录结构照惯例（`plugin.toml` / `config.yaml` / `main.py` / `models/` / `nodes/`），`nodes/` 下**一个事件一个文件**：
  - `on_agent_start` → `Goto(ON_TURN_START)`
  - `on_turn_start` → `Goto(ON_BEFORE_REQUEST)`
  - `on_before_request` → `Goto(ON_REQUEST)`
  - `on_request` → `Goto(ON_AFTER_REQUEST)`
  - `on_after_request` → **分支**：末条消息带 `tool_calls` → `Goto(ON_TOOL_CALLING)`，否则 → `Goto(ON_TURN_END)`（由 `is_tool_calling(messages)` 判定）
  - `on_tool_calling` → `Goto(ON_TURN_START)`
  - `on_turn_end` → `Goto(ON_AGENT_END)`
  - `on_agent_end` → `Goto(END)`（`END` 被 langgraph 过滤，于是没有下一跳、图就此结束）
- **`consts/node_priorities.py` 扩为九档等比阶梯**：`MAXIMUM` / `HIGHEST` / `HIGH` / `MEDIUM` / `NORMAL` / `LOW` / `LOWEST` / `TRIVIAL` / `MINIMUM`，九个名字经 `consts/__init__.py` 全量导出

### Changed

- **优先级常量 `EARLIEST` / `LATEST` → 九档阶梯（破坏性）**：`EARLIEST`(200) 与 `LATEST`(-200) 两个名字删除，原 `NORMAL`(0) 保留。`register()` 仍是 `sort(key=…, reverse=True)`，**数值大的先跑**
- **`base_topology` 注册在 `MINIMUM`（不是 `TRIVIAL`）**：它是绝对地板，保证「任何插件、任何档位都能抢在默认跳转前面」。`MAXIMUM` / `MINIMUM` 在这里是**可用档位**而非「禁止使用的哨兵」—— 若后续想改成哨兵语义，把默认跳转挪到 `TRIVIAL` 即可
- **`ON_TOOL_CALLING` 的下一跳由 `ON_BEFORE_REQUEST` 改为 `ON_TURN_START`（有意为之）**：旧 `wire()` 的静态边是 `ON_TOOL_CALLING → ON_BEFORE_REQUEST`，新默认跳转改成回 `ON_TURN_START`，即**每轮工具调用都重走一遍「轮开始」**（`build_client` 会重建一次 `Chat[OI]`，幂等，代价是多一次对象构造与配置查找）。这是刻意模仿 pi 的回合语义，**不是笔误**

### Fixed

- 🔴 **`consts/node_priorities.py` 语法错误（`import miaoli_bot.consts` 直接 `SyntaxError`）**：草稿里 `HIGHEST` / `HIGH` / `MEDIUM` / `LOW` / `LOWEST` / `TRIVIAL` 六个名字写成了空值（`HIGHEST\t= ` 没有右值），Python 解析即失败
- 🔴 **`consts/__init__.py` 导出没跟上改名（`ImportError`）**：文件已换成九档阶梯，导出表却仍是 `from .node_priorities import EARLIEST, LATEST, NORMAL` —— 这两个名字在新文件里已不存在。导入块与 `__all__` 同步换成九个新名
- **`plugins/base_topology/main.py` 的 `LATEST` 引用（共 8 处 + 1 处 import + 1 处 docstring）**：全仓唯一还在用旧名的地方，改为 `MINIMUM`
- **`nodes/on_after_request.py` / `nodes/on_turn_end.py` 两处语法错误**：前者 `def is_tool_calling(messages: ???)` 的 `???` 不是合法类型注解，后者 `async def (state: …)` 缺函数名 —— 两个文件都编译不过。已分别补为 `List[BaseMessage]` 与 `on_turn_end`
- **8 个节点文件全部缺导入**：只有 `GraphRuntimeContext` / `GraphState` / `Runtime`，裸用 `Goto` / `ON_*` / `END` / `BaseMessage` 会在运行时 `NameError`。已按需补齐，并删掉 `on_after_request.py` 里没用上的 `tools_condition` 导入
- **`is_tool_calling` 的返回类型与注解不符**：`return messages and getattr(…)` 在 `messages` 为空时返回 `[]` 而非 `bool`（注解写的是 `-> bool`），改为 `bool(…)`
- **`nodes/__init__.py` 导出为空**：补齐 8 个节点函数的导出

### Note

- **破坏性清单**（升级需同步改动）：① 优先级常量 `EARLIEST` / `LATEST` 已删除，改用九档阶梯中的对应档位。**其余 5 条 0.10.0 的破坏性变更仍然有效**（事件名 / `core/graph/graph_pipeline.py` 路径 / `consts/graph_events.py` + `node_priorities.py` 路径 / `Update` 类删除 / `PipelineStopDispatch` 不再被 `_dispatch` 捕获）
- **验证**（真跑）：① `compileall` 全仓 rc=0；② `ruff --select F401,F811,F841` 全仓只剩 `main.py:158` 一处既有 F841；③ `consts.__all__` 共 28 项**逐项可解析**，九档阶梯导入值 `9999 1000 100 10 0 -10 -100 -1000 -9999`，严格递减与上下对称均成立；④ 全量插件加载 **10/10**（新增 `base_topology`），8 个事件的处理器列表**末位均为默认跳转且 `priority=-9999`**；⑤ **端到端正常路径**（真插件 + 真 config + 假模型）—— `final_answer='（假模型回复）'`、消息序列 `[HumanMessage, AIMessage]`；⑥ **端到端工具路径** —— 轨迹 `… → after_request → tool_calling → turn_start → before_request → request → after_request → turn_end → agent_end`、模型调用 **2** 次、消息序列 `[HumanMessage, AIMessage, ToolMessage, AIMessage]`、`final_answer='结果是 3'`；⑦ **覆盖能力** —— 在 `ON_AGENT_START` 额外挂一个 `NORMAL` 优先级的「抢跑」处理器返回 `Goto(ON_AGENT_END)`，轨迹为 `['inject_account', 'format_input', 'hijack']`，**默认跳转被短路、未执行**；⑧ 回归套件 `accumulate_unit_test` **27/27**、`fixer_test2` **31/31**、`candidate_g_test` **18/18**、`compact_dispatch_check` **7/7**
- **未验证**：NcatBot 运行时下的端到端对话（`on_message` → 发送循环）仍未跑；本版**只在真实插件 + 真实 config + 假模型下验证**，未真实调用 LLM 端点
- **待清理**（本次未动，沿用 0.10.0）：`errors/pipeline_stop_dispatch.py` 已无消费方；`main.py:158` 的 F841；`_compact.py` 的 `CONTEXT_WINDOW` 仍是硬编码 `128000`

### Future

- 🐛 **`system_prompt` 通道的覆盖问题（已知 Bug，待重新设计）**：`GraphState.system_prompt` 是**普通键**（无 reducer → last-write-wins），于是**多个子插件往同一通道注入时，后写的会静默覆盖先写的** —— 实测 `NORMAL+1` 的注入者内容被 `NORMAL` 的注入者整个吞掉。但这个键当初写成普通键是有原因的：它需要「每轮重置、跨轮不累积」，而单纯的 concat 通道（`operator.add`）会让片段逐轮累加（实测 3 轮后 `'AAA'`）。**两条需求相互冲突** —— 多插件共存要求「追加」，跨轮干净要求「重置」，因此必须「concat 通道 + 每轮用 `Overwrite` 重置」两件事一起做（已实测该组合可行：3 个片段全在、顺序稳定、跨轮不累积；重置节点须挂最高优先级 `MAXIMUM`，且必须用 `Overwrite` 而非直接写值，否则仍会被 reducer 当成追加）。**当前未落地，方案与实测数据见开发记录**；触发条件是「有第二个子插件需要注入提示词」，现在只有一个注入者（`account_injector`），暂无实际影响。

## [0.10.0] - 2026-10-04

> 🔧 **`GraphPipeline` 重构：拓扑从「静态边」改为「事件节点 + 主动跳转」，控制流从异常改为返回值（破坏性）**。`wire()` 不再定义任何事件顺序 —— 它只挂 8 个事件节点和一条入口边（`START → ON_AGENT_START`），「下一个事件是谁」改由**处理器主动返回跳转指令**决定。为此新增 `core/graph/actions/` 四件套：空基类 `BaseAction`，与 `Continue`（停止本事件剩余处理器）/ `Goto`（跳到指定事件）/ `Abort`（中止整轮图）三个 Action，各自可携带 `updates` 增量。**顺带把「纯增量」的表达统一成裸 `dict`** —— 原来的 `Update` 包装类整个删除，节点直接 `return {...}` 即可，现有子插件**零改动**。同时收口命名：事件名去掉 `miaoli_bot/` 前缀（`__on_agent_start__` 等）、优先级常量 `MAX_PRIORITY` / `MIN_PRIORITY` / `DEFAULT_PRIORITY` → `EARLIEST` / `LATEST` / `NORMAL`、模块 `core/graph_pipeline.py` → `core/graph/graph_pipeline.py`。
>
> ⚠️ **本次是破坏性变更，且图当前无法端到端跑通**：`tools_condition` 条件边随 `wire()` 一起删除，而替代它的「默认跳转」（`ON_AFTER_REQUEST` 该去 `ON_TOOL_CALLING` 还是 `ON_TURN_END` 的分支判断）**尚未实现**。当前 edgeless 拓扑下，若某事件的处理器全部只返回增量 dict（不返回 `Goto`），该节点就没有下一跳，langgraph 视为终点 —— **整张图静默结束**，`final_answer` 缺失，`main.py` 随即 `KeyError`。补齐默认跳转插件前，请勿把本版部署到运行环境。

### Added

- **`core/graph/actions/`（新包，4 个 Action）**：`BaseAction` 是空基类，`Continue` / `Goto` / `Abort` 都直接继承它（**不再经 `Update` 中转**）。三者都有 `updates: Delta = None`，在 `__init__` 里各自赋值（不依赖父类 `__init__`）：
  - **`Continue`** —— 停止本事件剩余处理器，已累积的增量照常返回（替代旧 `PipelineStopDispatch` 的 `break` 语义）
  - **`Goto(goto, updates)`** —— 跳到 `goto` 指定的节点，`updates` 随 `Command` 一起提交。`GotoTarget = Union[str, Send, List[Union[str, Send]]]`，**传列表是扇出**（并行执行、写同一通道会 `InvalidUpdateError`），不是「依次执行」
  - **`Abort(reason, updates)`** —— 中止整轮图运行，`_dispatch` 把它转成 `AgentAborted` 抛出；`reason` 空值时兜底为 `"null"`
- **`consts/graph_events.py` / `consts/node_priorities.py`**：原 `consts/graph.py` 按语义一拆为二，两者都经 `consts/__init__.py` 导出

### Changed

- **`wire()` 改为 edgeless**：删除全部 8 条静态边（`ON_AGENT_START → ON_TURN_START → … → ON_AGENT_END`）与 1 条条件边（`add_conditional_edges(ON_AFTER_REQUEST, tools_condition, …)`），只保留 `add_edge(START, ON_AGENT_START)` 作为入口。**图不再定义顺序，只定义事件节点与起点**
- **`_dispatch` 的控制流改为「读返回值」**：handler 的返回值改称 `action`，判定链为 —— `is_none_action`（`None` → 无操作、`continue`）→ `is_update_action`（裸 dict 或 Action 自带 `updates` → 折叠进增量）→ `isinstance(action, Continue)` → `break`；`Goto` → `return Command(goto=…, update=updates)`；`Abort` → `raise AgentAborted(…)`；其余非 `BaseAction` / 非 `dict` → 打「未知的 Action」日志。**`Command` 是「短路」不是「追加」** —— 第一个返回 `Goto` 的处理器即终止本事件剩余处理器
- **`is_update_action` 收窄为「裸 dict 或 Action 自带的 dict 增量」**：`isinstance(action, dict) or (hasattr(action, "updates") and isinstance(action.updates, dict))`。**必须同时认这两条** —— 只认 `dict` 会让 `Goto(updates=…)` / `Continue(updates=…)` / `Abort(updates=…)` 的增量被静默丢弃（实测：`Goto` 带的 `Overwrite` 丢失后 `messages` 不再被替换）；只认 Action 会让现有 6 个返回裸 dict 的节点全部失效
- **`_merge` / `_accumulate` 搬出类成为模块级纯函数**，并更名 `merge_data` / `accumulate_data`（纯函数不该挂在类上）；`_dispatch` 内局部变量 `_view` / `_updates` 一并去掉下划线
- **`models/runtime/handler.py`**：`Handler.function` 的类型注解从占位符 `Callable[..., ...]`（`...` 不是合法类型）改为 `Callable[..., Awaitable[Any]]`
- **事件名去掉 `miaoli_bot/` 前缀**：`miaoli_bot/graph.event.on_agent_start` → `__on_agent_start__`（8 个全改），框架不再硬编码任何应用专属字符串
- **优先级常量更名**：`MAX_PRIORITY`(200) → `EARLIEST`、`MIN_PRIORITY`(-200) → `LATEST`、`DEFAULT_PRIORITY`(0) → `NORMAL`。`register()` 仍是 `sort(key=…, reverse=True)`，**数值大的先跑**
- **4 个子插件同步更名**：`account_injector` / `base_nodes` / `orphan_tool_fixer` / `pending_tool_fixer` 的 `from miaoli_bot.consts import DEFAULT_PRIORITY` → `import NORMAL`（共 11 处引用），优先级相对关系（`NORMAL+1` / `NORMAL-1` / `NORMAL+2` / `NORMAL+3`）不变
- **`_dispatch` 的异常日志补回异常消息**：`LOGGER.exception(f"… 出现错误 {type(e).__name__}")` → `… {type(e).__name__}: {e}"`

### Removed

- **`core/graph/actions/update.py`（`Update` 类整个删除）**：「纯增量」的表达统一为裸 `dict`。删除理由是它的存在与「能带增量」这件事无关 —— 后者是**属性**（`hasattr(action, "updates")`）不是**类型**，用类来查属于构造性错误；而它作为「已知但无需分支」的落底项，职责已被 `dict` 接管
- **`consts/graph.py`**：拆成 `graph_events.py` + `node_priorities.py`
- **`core/graph_pipeline.py`（旧路径）**：搬至 `core/graph/graph_pipeline.py`
- **`_dispatch` 的 `except PipelineStopDispatch` 分支**：被 `Continue` 返回值取代。**注意** `errors/pipeline_stop_dispatch.py` 的类本身**仍然存在且仍在 `errors` / 根包导出**（删它是破坏性变更，本次未动），只是全仓已无 raise 方与 except 方

### Fixed

- 🔴 **`self._merge` / `self._accumulate` 找不到（每轮对话必炸）**：两个函数搬出类之后，`_dispatch` 里三处调用点没跟上，仍是 `self._merge(...)` 形式 → `AttributeError: 'GraphPipeline' object has no attribute '_merge'`
- 🔴 **`AgentAborted(handler=handler, reason=…)` 签名不符**：`AgentAborted.__init__` 只接受 `reason` → `TypeError`。改为 `AgentAborted(reason=(action.reason or "null"))`
- 🔴 **`BaseAction` 使用了但没导入**：`_dispatch` 的兜底分支 `if not isinstance(action, BaseAction)` → `NameError`（该分支在 `for` 循环里每个 handler 都会走到，`NameError` 又不在 `try` 内、不被 `except Exception` 接住 → 整轮图崩）
- 🔴 **`is_update_action` 的 `instance_check` 放行 `update=None`**：`isinstance(action, Update)` 对 `Update()`（`updates` 为 `None`）与 `Update(update="字符串")` 都返回 `True`，于是走到 `accumulate_data(updates, None, …)` → `new_data.items()` → `AttributeError`（同样在 `try` 之外 → 整轮图崩）。而唯一有用的形态 `Update(update={...})` 本来就被鸭子类型接住了，**该分支净贡献为零、只多买两个崩溃**
- **`actions/*.py` 一个 import 都没有**：四个 Action 文件原本裸用 `Optional` / `Any` / `Dict` / `Send`（运行时 `NameError`）；`goto.py` 的 `goto: ???` 与 `handler.py` 的 `Callable[..., ...]` 同为占位符。类型注解与 import 已补齐
- **`continue.py` → `continue_.py`**：`from .continue import …` 是 `SyntaxError`（`continue` 是 Python 关键字）
- **`hasattr(action, update)` 缺引号**（`NameError`）与 **`accumulate_data(updates, action, …)` 该传 `delta`**（传了整个 Action 对象）
- **`Delta` 曾重复定义 4 份**：收口到 `base_action.py` 一处（`Delta = Optional[Dict[str, Any]]`），其余三个 Action 从它导入；`goto.py` 里那份是死代码（定义了却没用）

### Note

- **破坏性清单**（升级需同步改动）：① 事件名（若你自建子插件直接写过 `"miaoli_bot/graph.event.*"`）；② `MAX_PRIORITY` / `MIN_PRIORITY` / `DEFAULT_PRIORITY` 三个常量名；③ `core/graph_pipeline.py` 的导入路径；④ `consts/graph.py` 的导入路径；⑤ `Update` 类（改用裸 dict）；⑥ `PipelineStopDispatch` 不再被 `_dispatch` 捕获
- **验证**（真跑）：① `compileall` 全仓 rc=0；② `ruff --select F401,F811,F841` 全仓只剩 `main.py:158` 一处 F841（`except AgentAborted as e:` 的 `e` 未使用，属既有）；③ 全量插件加载 **9/9**、注册工具 **15** 个；④ 四 Action 真跑 —— 裸 dict `{'final_answer': '裸dict'}` / `None` → `{}` / `Continue(updates={…})` → `{'final_answer': 'C'}` / `Continue()` → `{}` / `Goto(goto=X, updates={…})` → `Command(update={'final_answer': 'G'}, goto='__on_turn_start__')` / `Goto(goto=X)` → `Command(goto='__on_turn_start__')` / `Abort(reason='忙')` → `AgentAborted('忙')` / 未知 `object()` → `{}` + 日志；⑤ **端到端 Goto 链**：`RUN=['start','turn','end']`、`final_answer='答完了'`、`messages=['答完了']`（`Goto(updates={"messages": Overwrite([…])})` 的 `Overwrite` 正确生效、末尾裸 dict 正常收尾）；⑥ `AgentAborted.__mro__` = `AgentAborted → GraphBubbleUp → Exception → BaseException`
- **未验证**：NcatBot 运行时下的端到端对话未跑；**图当前不能端到端跑通**（缺默认跳转插件，见开头警告）；`orphan_tool_fixer` / `pending_tool_fixer` 的优先级关系在新常量名下未重跑 `fixer_test2`
- **待清理**（本次未动）：`errors/pipeline_stop_dispatch.py` 已无消费方；`main.py:158` 的 F841；`plugins/` 下 6 个节点返回裸 dict 的写法现在**合法且是推荐写法**，无需迁移

## [0.9.12] - 2026-10-03

> 🐛 **修复 `GraphPipeline` 增量归约不满足结合律的 bug（0.9.11 及之前的已发布代码里潜伏），并新增两个坏历史修复子插件**：`_dispatch` 把同一事件里各 handler 的返回值两两折叠时走的是 `add_messages`，而它**只在新来的那一份里找 `REMOVE_ALL_MESSAGES` 标记**，于是后一次「整表重写」会把前面积累的删除指令**静默丢弃**。修法是把「累积增量」与「增量 → 视图」两条路径拆开：新增 `_accumulate` 专管前者（让替换包装活到框架真正应用增量的那一刻），`_merge` 一行未动继续只负责后者。同时把「整表重写」的表达从 langchain 内部哨兵 `RemoveMessage(id=REMOVE_ALL_MESSAGES)` 换成 langgraph 官方 `Overwrite` —— 插件侧不再手搓内部哨兵，框架也不再解析它。**另外子插件目录 `account_inject/` 改名为 `account_injector/`**（入口类 `AccountInjector` 与 `plugin.toml` 的 `enter_class` 不变），README / `config.example.yaml` 里的引用同步收口。

### Added

- **`plugins/pending_tool_fixer/`（新子插件，入口类 `PendingToolFixer`）**：在 `ON_BEFORE_REQUEST`（`priority=3`）修复**悬空的工具调用** —— 存在发起但不存在返回的 `tool_call` 时，在每个悬空 `AIMessage` 之后插一条合成 `ToolMessage`（`id=f"auto-fix: {tool_call_id}"`、`status="error"`、`name` 取工具名、`content` 取自带 `config.yaml` 的 `fix_message`），返回 `{"messages": Overwrite(整表)}`。**历史本就合法时返回 `None`**（`fixed == 0` 即早返回）—— 这条守卫是必需的，否则每轮都会把整张消息表写进 `checkpoint_writes`
- **`plugins/orphan_tool_fixer/`（新子插件，入口类 `OrphanToolFixer`）**：在 `ON_BEFORE_REQUEST`（`priority=2`）修复**孤儿工具返回** —— 删掉「找不到发起它的 `tool_call`」的 `ToolMessage`，**只产出定向删除增量**（`[RemoveMessage(id=m.id) for m in orphans]`），比整表重写更省；无孤儿时返回 `None`
- **`utils/sugar.py` 新增 `get_thread_id` / `get_tool_calls`**：前者从 `langgraph.config.get_config()` 取当前 `thread_id`、**图外调用抛 `RuntimeError` 时兜底返回 `"unknown"`**（`on_load` / `on_close` / 裸协程里不能直接调，插件里也只用它打日志）；后者取 `message.tool_calls or []`。两者经 `utils/__init__.py` 导出，两个修复插件共用（插件自带的 `utils/sugar.py` 只留各自的业务约定：`fix_tool_message` 的 `auto-fix:` 前缀 / `declared_tool_call_ids`）

### Changed

- **`core/graph_pipeline.py` 新增 `_accumulate`（`_dispatch` 改用它折叠）**：与 `_merge` 的唯一区别是 **`Overwrite` 的包装必须留着** —— 它在这里被两两归约，若当场拆开，替换语义就丢了，后面再来的增量会被误当成追加。三分支：新来的要替换 → 直接接管；之前是替换 → `Overwrite(operator(old.value, value))` 叠在替换结果之上；否则 → `operator(old, value)`。`_merge` 相应地新增一个分支：`isinstance(value, Overwrite)` → `merged[key] = value.value`（处理器与视图拿到的必须是普通值），**其余一行未动**
- **`plugins/base_nodes/nodes/_compact.py`**：「整表替换」由 `[RemoveMessage(id=REMOVE_ALL_MESSAGES), 摘要, *保留窗口]` 改为 `Overwrite([摘要, *保留窗口])`，`RemoveMessage` / `REMOVE_ALL_MESSAGES` 导入随之删除
- **`plugins/account_inject/` → `plugins/account_injector/`**：目录改名（入口类 `AccountInjector` 与 `plugin.toml` 的 `enter_class` 不变，`SHARE_STORE` 键随包名自动变成 `miaoli_bot/subplugin/account_injector.*`）；README（特性说明 / 目录结构 / 数据流 / 子插件表 / 配置表）与 `config.example.yaml` 的注释同步收口，全仓再无旧名引用
- **`models/config/provider.py`**：`LLM.visions` → `LLM.support_visions`（与 `config.example.yaml` 同步）；`Vision` 字面量去掉 `tool_calls`（模态输入不该混入工具能力描述）；`Provider.models` 加 `min_length=1`
- **`models/config/plugin.py`**：`providers` 加 `min_length=1`（空供应商字典直接在校验期拒绝，不再等到建图时才 `KeyError`）
- **`plugins/base_nodes/nodes/latest_to_answer.py`**：末条不是 `AIMessage` 时，兜底文案从固定的 `"我就是Bug."` 改为提示 `最后一条非 AIMessage 信息 ({类型})\n请携带 thread_id={id} 向管理员反馈`（`get_config()` 只在非 `AIMessage` 分支才调，正常回复不走那里）

### Fixed

- 🔴 **`GraphPipeline._dispatch` 的增量折叠不满足结合律（0.9.11 及之前的已发布代码里潜伏的 bug）**：`_dispatch` 此前用 `_merge` 折叠各 handler 的产出，而 `_merge` 走 `add_messages` —— 后者**只在 `right` 里找 `REMOVE_ALL_MESSAGES`**（`langgraph/graph/message.py`：`if remove_all_idx is not None: return right[remove_all_idx + 1:]`），`left` 被整个丢弃。于是「handler A 定向删了 x」+「handler B 整表重写」在同一超步里相遇时，**删除指令被静默吞掉、x 复活**。**实际后果**：`compact`（`priority=1`）与 `call_llm`（`priority=0`）的优先级一旦反序，压缩就被整个吞掉 —— 实测 30 条消息不降反升到 32 条（修后 30 → 6）。**注意**：langgraph 自己也用同一条（有缺陷的）归约规则，所以拆成独立节点、自定义 reducer 都救不了（前者并行节点共享旧快照、后者拿到的 `left` 已物化，删除是「缺席」而非「记录」），只能在框架的折叠层解决
- **`plugins/base_nodes/nodes/_compact.py` 的既有隐患**：上述 bug 的既有受害者 —— 它一直是 `ON_REQUEST` 里唯一用整表重写的节点，与 `call_llm` 的追加同超步折叠，反序时压缩被吞。本次改 `Overwrite` 后，**与其它处理器的「追加 / 定向删除」可以任意顺序组合**
- **`pending_tool_fixer` 的守卫缩进**：`if not fixed:` 的 `return` 曾误缩进进 `if` 体内，语义整个颠倒 —— `fixed == 0` 时反而返回 `Overwrite(整表)`（每轮写爆 `checkpoint_writes`），真需修复时却隐式返回 `None`。已改为 `if not fixed: return None`，日志与返回体放在守卫之后

### Note

- **验证**（真跑，共 **98 项断言**）：① `fixer_test2` **31/31** —— 两个插件真加载与注册、**真实坏数据**（服务器 `private-3640942712` 的 checkpoint `1f1be453-88be-659e-8789-b64c7bfcd617`，550 条）修复后 **550 → 551 条**且原有消息一条不少、顺序不变，优先级正/反序结果等价，幂等（修好后再跑无 `messages` 写入），八项边界；② `accumulate_unit_test` **27/27** —— 不含 `Overwrite` 时 `_accumulate` 与 `_merge` 逐位一致、替换+追加/删除双序、两次替换、非 `messages` 通道、空增量、真实 `_dispatch` 协同；③ `candidate_g_test` **18/18**；④ `compact_dispatch_check` **7/7** —— 正序 30 → 7、反序 30 → 6（修前反序 30 → 32）；⑤ `overwrite_graph_e2e_test` **15/15** —— 真实编译图 + checkpointer，含**通道还没有值时的首写 `Overwrite`**（langgraph 自己在 `update` 里处理了 MISSING）与「持久化后通道里是普通 list 而非 `Overwrite` 对象」；⑥ 全量插件加载 **9/9**（`account_injector` / `base_nodes` / `base_parsers` / `base_platform_tools` / `base_system_tools` / `meme_extension` / `orphan_tool_fixer` / `pending_tool_fixer` / `tool_permission_manager`），节点注册顺序不变；⑦ 端到端 `ainvoke` 管理员可见 **15** 工具 / 路人可见 **9** 工具；⑧ `compileall` 全仓 rc=0、`ruff --select F401,F821,F811` 全过
- **存储代价**（实测，sqlite checkpointer，400 条历史）：`Overwrite` 与旧的 `RemoveMessage` 哨兵**同级** —— 纯追加时节点自身写入 **184 字节**，整表替换时 `Overwrite` 257,335 字节 vs 哨兵 257,432 字节（差 97 字节只是包装开销）。另外顺带省掉两处遍历：`_accumulate` 不再扫列表找标记（折叠 1.2~1.3×），`_merge` 的替换分支从 O(n) 全表拷贝降为 O(1) 直接换值
- **未验证**：NcatBot 运行时下的端到端对话（`on_message` → 发送循环）未跑；两个修复插件在真实运行环境里对「上一轮异常中断」的修复效果未观测（只用真实坏数据 checkpoint 验证了修复正确性）；`_compact.py` 的 `CONTEXT_WINDOW` 仍是硬编码 `128000`

## [0.9.11] - 2026-10-02

> 🧩 **LLM 实例改为图内按需创建，并补齐这轮重构留下的坑**：`ChatOpenAI` 不再在 `main.py` 里硬编码（`model="deepseek-flash"` + `providers[0]`），改为 `main.py` 只把 `provider_name` / `model_name` 两个**名字**写进 state，由新节点 `build_client`（挂 `ON_TURN_START`）读根配置建实例、写进 `runtime.context["client"]`；`runtime.context["chat_model"]` 随之更名 `client`。`format_prompt` 从 `base_nodes` 拆出，独立成子插件 `account_inject`（`ON_AGENT_START`），配置读取统一走 `SHARE_STORE`。`providers` / `models` 由 list 改为 dict，`name` 字段交给字典键承担。**本版同时修掉这轮改动里 4 个必崩项、模板脱节与 3 处多余导入**（详见 `### Fixed`）。

### Added

- **`plugins/base_nodes/nodes/build_client.py`（新节点，挂 `ON_TURN_START`）**：从 `SHARE_STORE` 取根配置，按 `state["provider_name"]` / `state["model_name"]` 定位 `Provider` / `LLM`，用 `base_url` / `api_key` / `max_tokens` 建 `ChatOpenAI` 写入 `runtime.context["client"]`。**刻意不在此处 `bind_tools`** —— 工具表由 `tool_permission_manager` 按身份每请求裁剪，绑定必须留在 `call_llm` 调用点（`bind_tools` 返回新对象，不会污染已建实例）
- **`plugins/account_inject/`（新子插件）**：把原 `format_prompt` 的账号注入职责独立成插件 —— `inject_account`（`ON_AGENT_START`）拼 `<administrator_QQ_number>` / `<administrator_nickname>` / `<bot_QQ_number>` / `<bot_nickname>` 四块，与 `cfg.system_prompt` 以空行拼接写进 `system_prompt`。入口类 `AccountInjector`
- **`consts/graph.py` 的 `DEFAULT_PRIORITY = 0`**：节点注册的默认优先级常量（经 `consts/__init__.py` 导出），`base_nodes` / `account_inject` 的 `on_load` 全部改用它，不再散落字面量
- **`GraphState` 新增 `provider_name: str` / `model_name: str`**：由 `main.py` 每请求写入，供 `build_client` 选模型；同时把 `messages` 提到字段首位
- **`models/config/__init__.py` / `models/__init__.py` 导出 `LLM` / `Provider`**：此前只能从 `models.config.provider` 深处导入

### Changed

- **`models/config/provider.py`**：`Provider` / `LLM` 的 `name` 字段删除（改由字典键承担）；`LLM.protocol` 由带默认值改为**必填**；`visions` 加 `min_length=1`；`Vision` 字面量 `tool_calling` → `tool_calls`；`Protocol` 字面量 `openai-completion` → `openai-completions`
- **`models/config/plugin.py`**：`providers` 由 `List[Provider]` → `Dict[str, Provider]`，`Provider.models` 由 `List[LLM]` → `Dict[str, LLM]`
- **`models/graph_runtime_context.py`**：`chat_model: BaseChatModel` → `client: Optional[BaseChatModel]`（进图时为 `None`，由 `build_client` 在 `ON_TURN_START` 填）；删除 `plugin_config` 字段（配置统一走 `SHARE_STORE`）
- **`main.py`**：删掉硬编码的 `ChatOpenAI(...)` 与 `langchain_openai` 导入；改为把首个供应商/模型名写进 state，`context` 变为 `{"client": None, "tools": ...}`
- **`plugins/base_nodes/main.py`**：移除 `on_before_request(format_prompt)`，新增 `on_turn_start(build_client)`；所有优先级改用 `DEFAULT_PRIORITY`（`attach_image` 由 `-10` → `DEFAULT_PRIORITY-1`）
- **`plugins/base_nodes/nodes/call_llm.py` / `_compact.py`**：`chat_model` → `client`（`call_llm` 内 `assistant_msg` → `AI_message`）
- **`plugins/base_nodes/nodes/_compact.py`**：摘要指令由第一人称改为第三人称
- **`plugins/tool_permission_manager/config.yaml`**：`archive_meme` 的权限由 `anyone` 收紧为 `admin`（归档表情包会写库，按可写类工具对待）
- **`config.example.yaml`**：`providers` 迁移到 dict 结构，补齐 `protocol` / `context_window` / `max_tokens` / `visions`（新 schema 下均为必填或至少一项）；账号段注释由已删除的 `format_prompt` 更正为 `account_inject` 子插件的 `inject_account`
- **`errors/pipeline_stop_dispatch.py`**：docstring 补「不继承 `BaseBotError`」的设计说明（纯注释）

### Fixed

- **`main.py` 的供应商/模型选择**（🔴 每条消息必崩）：`plugin_cfg.providers.keys()[0]` —— `dict_keys` 不可下标（`TypeError`），且下一行的 `provider` 从未定义（`NameError`）。改为 `next(iter(...))`
- **`plugins/base_nodes/nodes/build_client.py` 缺导入**（🔴）：用了 `SHARE_STORE` 与 `PLUGIN_CONFIG` 却都没导入，`ON_TURN_START` 一到就 `NameError`
- **`models/config/plugin.py` 缺 `Dict` 导入**（🔴）：`providers` 改成 `Dict[str, Provider]` 后 typing 行没补 `Dict`，pydantic 建 schema 解析注解即抛 `NameError`
- **`plugins/base_nodes/main.py` 残留 `inject_account` 导入**（🔴）：该节点已迁至 `account_inject` 子插件，`nodes/__init__.py` 不再导出，`from .nodes import (...)` 直接 `ImportError`
- **`config.example.yaml` 未随 schema 迁移**：`providers` 还是旧 list 结构，照抄模板即 `ValidationError`
- **3 处多余导入**：`main.py` 的 `InMemorySaver`、`models/config/plugin.py` 的 `List`、`plugins/account_inject/main.py` 的 `Registry`（全仓 `ruff --select F401` 复查为零）
- **`plugins/account_inject/main.py` 类名**：`BaseNodes` → `AccountInjector`（从 `base_nodes` 复制时的残留），`plugin.toml` 的 `enter_class` 同步

### Removed

- **`plugins/base_nodes/nodes/format_prompt.py`**：职责迁至 `account_inject` 子插件的 `inject_account`

### Note

- **验证**（真跑）：① `compileall` 全仓 rc=0、`ruff --select F401` 全仓 `All checks passed!`；② 全量插件加载 **7/7**（`account_inject` / `base_nodes` / `base_parsers` / `base_platform_tools` / `base_system_tools` / `meme_extension` / `tool_permission_manager`），节点注册为 `ON_AGENT_START=[inject_account(0), format_input(0)]`、`ON_TURN_START=[build_client(0)]`、`ON_BEFORE_REQUEST=[pick_tools(1)]`、`ON_REQUEST=[compact(1), call_llm(0)]`、`ON_TOOL_CALLING=[invoke_tools(0), attach_image(-1)]`、`ON_AGENT_END=[latest_to_answer(0)]`；③ `config.example.yaml` 与根 `config.yaml` 均过 `PluginConfig` 校验；④ **真实 `GraphPipeline` 端到端 `ainvoke`**（真插件 + 真 config + 替换掉实例化来源的假模型）：`build_client` 收到的构造参数为 `model=deepseek-flash` / `base_url=https://api.deepseek.com/v1` / `api_key=sk-…` / `max_tokens=4096`，管理员可见 **15** 个工具、路人可见 **9** 个（与权限表 `admin × 6` + `anyone × 9` 自洽），`system_prompt` 已注入账号信息，`final_answer` 正常产出
- **未验证**：NcatBot 运行时下的端到端（`on_message` → 发送循环）未跑；`_compact.py` 的 `CONTEXT_WINDOW` 仍是硬编码 `128000`，尚未接到 `LLM.context_window`
- **已知边界**：模型选择仍是「取根配置里第一个供应商的第一个模型」（`main.py` 内标着 `# HACK: 依旧技术债`），尚未提供配置项

### Docs

- **CHANGELOG 新增本条目**（README 尚未同步至 0.9.11）

## [0.9.10] - 2026-10-01

> 🛑 **`_dispatch` 加错误处理，并新增「停止分发」信号 `PipelineStopDispatch`**：此前 `_dispatch` 明确标着「先不写错误处理」（`# NOTE`），handler 里抛任何异常都会直接冒到 langgraph。现在每个 handler 被 `try` 包住，并按三类分流 —— 抛 `PipelineStopDispatch` 即**停止本事件剩余 handler**（已累积的增量照常返回，后续事件不受影响）；langgraph 的控制流异常（`GraphBubbleUp`，含 `GraphInterrupt` 等）**原样透传**；其它异常**记录 traceback 后跳过该 handler，继续执行本事件剩余 handler**（**行为变更**：旧行为是直接冒到 langgraph）。**另外修复 `attach_image` 的优先级倒挂** —— 它此前排在 `invoke_tools` **之前**（`10 > 0`，而 dispatch 是降序执行），导致「把图片从 ToolMessage 搬进 HumanMessage」的逻辑永远扫不到本轮工具消息、完全空转；改为负数后恢复生效。

### Added

- **`errors/pipeline_stop_dispatch.py` 的 `PipelineStopDispatch`**：handler 抛它即可停止当前事件的后续 handler，用于「本事件到此为止」这类受控提前退出。经 `errors/__init__.py` 与根 `__init__.py` 导出（根包 `__all__` 顺带补上 `BaseBotError`，并加了 `# stores` / `# errors` 分组注释）
- **`core/graph_pipeline.py` 的模块级 `LOGGER`**：`get_log(__file__)`（`ncatbot.utils.logger` 的 `BoundLogger`，`exception()` 自带 traceback）

### Changed

- **`core/graph_pipeline.py` 的 `_dispatch` 错误处理**（三分类）：
  - `except GraphBubbleUp: raise` —— 显式放行 langgraph 控制流（`GraphInterrupt` / `ParentCommand` 等都是它的子类；若不单独列出会被下面的 `except Exception` 捕获）
  - `except PipelineStopDispatch: break` —— 停止本事件剩余 handler，已累积的 `_updates` 照常返回
  - `except Exception as e: LOGGER.exception(...); continue` —— 记录 traceback 后跳过当前 handler，**不中断**本事件，后续 handler 继续执行
- **行为变更**：普通 handler 异常此前会冒到 langgraph（中断整张图），现在被记录并跳过 —— 单个 handler 出错不再影响同一事件内的其它 handler
- **`core/graph_pipeline.py` 的 `_merge`**：注释从分支内部提到分支上方（纯注释调整，逻辑未变）

### Fixed

- **`_dispatch` 异常日志里的 `handler.__name__`**：`Handler` 是 dataclass、没有 `__name__`，异常分支自身会抛 `AttributeError`（把原始异常替换掉，且「记录后继续」完全失效）；改为 `handler.function.__name__`
- **`plugins/base_nodes/main.py` 的 `attach_image` 优先级倒挂**：`attach_image` 原注册为 `priority=10`、`invoke_tools` 为 `0`，而 dispatch 按 `priority` **降序**执行（大的先跑），于是 `attach_image` 总在 `invoke_tools` **之前**被调用 —— 此时本轮工具消息还没产生，它扫描「末尾连续 `ToolMessage`」恒为 0、直接 `return None`，图片搬运逻辑**从未生效**（`read_image` 等工具返回的 `image_url` 块一直原样留在 `ToolMessage` 里，而它自己的注释写明「AI Platform 的 tool 消息 content 只能是字符串」）。改为 `priority=-10`，排在 `invoke_tools` 之后执行

### Removed

- **`errors/api_unavailable_error.py`**：`APIUnavailableError` 全仓已无引用，删除；`errors/__init__.py` 的导入与 `__all__` 同步

### Note

- **验证**（真实 `GraphPipeline` 实测，`/tmp/ckpt_probe/dispatch_err_test.py`）：① priority 100 的 handler 增量在 `break` 后**被保留**（`system_prompt` 为改写值）；② priority 50 抛 `PipelineStopDispatch` 后 priority 0 的 handler **被跳过**；③ 同一请求的后续事件（`ON_AGENT_END`）**照常执行**，图正常完成；④ 对照实验：`ValueError` **不再冒泡**，日志出现 traceback，且同事件后续 handler 照常执行并生效
- **验证（`attach_image` 优先级修复）**（`/tmp/ckpt_probe/attach_fix_test.py`、`base_nodes_order_test.py`）：① 用真实 `BaseNodes.on_load` 注册后，`ON_TOOL_CALLING` 的排序为 `[invoke_tools(0), attach_image(-10)]`；② 真实 `GraphPipeline` + 真实 `invoke_tools` / `attach_image` 跑完整图 —— `priority=10`（旧）时图片**仍残留在 `ToolMessage`**、未进 `HumanMessage`（空转），`priority=-10`（新）时图片**已搬进 `HumanMessage`**、`ToolMessage` 变纯文本，且图正常终止
- **未验证**：`PipelineStopDispatch` 目前尚无实际业务消费方（属基础设施先行）；NcatBot 运行时下的端到端未跑；`GraphBubbleUp` 分支只验证了「不误吞」的代码路径，未构造真实 `GraphInterrupt` 场景
- **设计说明**：`PipelineStopDispatch` 直接继承 `Exception` 而非 `BaseBotError` —— 它是「控制流标志」而非「错误」，且只在本模块 `_dispatch` 内被捕获消费，不需要也不应被 `except BaseBotError` 之类顺手接住（已确认按此保持）

### Docs

- **README 更新至 0.9.10**：版本号 / `errors` 目录树（`api_unavailable_error.py` → `pipeline_stop_dispatch.py`）/ `graph_pipeline.py` 职责补「含错误处理」/ 项目状态新增本版段
- **CHANGELOG 新增本条目**

## [0.9.8] - 2026-10-01

> 🔍 **发送循环加调试日志**：`on_message` 在发送前打印两条 `logger.debug` —— 本次输出的字符数与「分隔符 + 切出的块数」，用来排查「一条回复被发成几条 / 没被切块」这类问题。

### Added

- **`main.py`（`on_message` 发送段）**：两条 `logger.debug` —— `输出 N 个字符`、`分隔符 'X' 分割出 N 个块`

### Fixed

- **`main.py`**：改名遗漏 —— `answer_chunks` 计算时误引用已不存在的 `raw_ot`（上一版把 `raw_ot` 更名为 `raw_output` 时漏掉这一处），会在**每条消息**上 `NameError`。现改为直接复用已提取的 `answer_string`

### Changed

- **`main.py`（`on_message` 发送段）**：变量语义化 —— `raw_ot` → `raw_output`、新增 `answer_string`（正文）与 `answer_chunks`（切块结果）、循环变量 `line` → `chunk`

### Note

- **验证**：AST 扫描 `on_message` 作用域确认无未定义名（此前正是该扫描发现的 `raw_ot` 遗漏）；模拟两种分隔符场景 —— `None` → 1 块发送 1 条、`"\n\n"` → 2 块发送 2 条，日志输出与发送条数均正确；全仓 `compileall` 通过
- **注意（日志可见性）**：`logger.debug` 的实际可见性由 NcatBot 的全局 debug 模式决定 —— `setup_logging(debug=…)` → `set_debug_mode()` 会把插件 logger 的级别设为 `DEBUG`（开）/ `INFO`（关）。当前运行配置 `/sdcard/Ncatbot_QQ/config.yaml` 是 `debug: false` + `logging.log_level: "ERROR"`，因此这两条日志**不会输出**；要看到需要开启 debug 模式
- **未验证**：NcatBot 运行时下的真实 QQ 发送未跑

### Docs

- **README 更新至 0.9.8**：版本号 / 项目状态新增本版段（含日志可见性提示）
- **CHANGELOG 新增本条目**

## [0.9.7] - 2026-10-01

> 🐞 **修复「未设置分隔符时回复被逐字拆成 N 条消息」**：`on_message` 的发送循环此前把两条分支混进同一个 `for` —— 有分隔符时 `.split()` 得到 `list`，无分隔符时直接用整个 `str`。当 `output.split_separator` 为 `null`（默认值）时，`for answer in final_answer` **迭代的是字符串本身，即逐字符**：一句话被拆成几十条 QQ 消息逐字发出，且每个字符都要 sleep 一次打字延迟。现已把切块收口到新增的 `utils.split_string`，它**恒返回 `List[str]`** —— `for` 拿到的必然是「块」而非「字符」。

### Fixed

- **`main.py`（`on_message` 发送循环）**：`output.split_separator` 为 `null` 时回复被逐字符拆分发送的问题。实测同一段 13 字文本：修复前发出 **13 条**、修复后 **1 条**。切块改由 `utils.split_string` 统一负责，不再把「整条」和「切好的块」两种类型混进同一个循环
- **`utils/sugar.py`**：补齐 `Optional` / `List` 类型导入 —— 此前靠 Python 3.14 的注解延迟求值（PEP 649）侥幸不在导入期报错，但 `typing.get_type_hints(split_string)` 会 `NameError`，任何做注解内省的调用方都会炸

### Added

- **`utils/sugar.py` 的 `split_string(string, separator=None) -> List[str]`**：分隔符为 `None` / 空串 → `[string]`（整条一块），否则 `string.split(separator)`。经 `utils/__init__.py` 导出（`__all__` 同步）

### Changed

- **`main.py`**：图返回值改称 `raw_ot`，切块结果称 `final_ot`，循环变量 `answer` → `line`，与 `split_string` 的引入配套
- **`utils/sugar.py` 的 `concatenate_id`**：签名由 `(session_id, is_group=False)` 收紧为 `(session_id, is_group)` —— 唯一调用处（`main.py` 的 `on_message`）本就显式传参，去掉默认值免得将来漏传时静默走私聊前缀

### Note

- **验证**（真跑）：`split_string` 五种分隔符（`None` / `""` / `"\n\n"` / `"||"` / 单字）与空串输入边界，全部恒返回 `list`；用修复前后的发送循环对比同一段文本，确认 13 条 → 1 条；`typing.get_type_hints()` 对 `split_string` / `concatenate_id` 均可解析；`concatenate_id` 两种分支输出正确（`group-` / `private-`）；全仓 `compileall` 通过
- **未验证**：NcatBot 运行时下的真实 QQ 发送未跑

### Docs

- **README 更新至 0.9.7**：版本号 / 功能特性（切块恒返回列表的语义）/ 目录树（`sugar.py` 职责补 `split_string`）/ 数据流第 9 步 / 项目状态新增本版段
- **CHANGELOG 新增本条目**

## [0.9.6] - 2026-10-01

> 🛡️ **新增 `tool_permission_manager` 子插件 —— 工具级权限控制**：按自带 `config.yaml` 的权限表（`admin` / `white_list` / `anyone`），在 `ON_BEFORE_REQUEST`（`priority=1`）把当前身份无权使用的工具从 `runtime.context["tools"]` 里摘掉。因为 `call_llm`（`bind_tools`）与 `invoke_tools`（`ToolNode`）读的是同一个 context，摘掉之后**模型看不见、执行器也拿不到** —— 这是一条真实的执行层白名单，不只是提示层过滤。未在权限表里声明的工具默认拒绝并打一条 warning。
>
> 🔨 **破坏性：`account` 字段改名** —— `root_id` → `admin_id`、`root_nickname` → `admin_nickname`；模型文件 `models/config/accounts.py` → `account.py`、类名 `Accounts` → `Account`（与 `Provider` / `LLM` 的实体命名一致，也避免被误读为 `List[Accounts]`）。**根目录 `config.yaml` 需同步改键名**，否则 `on_load` 校验会抛 `ValidationError`。

### Added

- **`plugins/tool_permission_manager/`（新增子插件）**：`config.yaml` 权限表 + `nodes/pick_tools.py`（`ON_BEFORE_REQUEST` 摘工具、`is_allowed` 纯函数判定）、`models/permission.py`（`Permission`：`tool_name` / `permission` / `white_list`）、`models/plugin_config.py`（`enable` / `permissions`）、`consts/share_store_keys.py`、`plugin.toml`、`README.md`
  - 三种权限语义：`admin`（比对根配置 `account.admin_id`）/ `white_list`（比对条目内名单）/ `anyone`（放行）
  - 未声明的工具 → **摘除 + warning**（默认拒绝，新增工具后必须补配置）
  - `enable: false` 时不注册节点，不做任何过滤
- **`plugins/tool_permission_manager/config.yaml`（内含权限模板）**：把当前全部 **15 个真实注册工具**写进权限表（`base_system_tools` / `base_platform_tools` / `meme_extension` 各 5 个），默认对可读写与执行类工具（`bash` / `read_file` / `write` / `replace` / `remove_meme_by_hash`）收紧为 `admin`，其余 `anyone`，并附 `white_list` 写法示例。
- **`plugins/base_system_tools/README.md`**：只列 5 个工具的用途（权限说明移交给 `tool_permission_manager`）。

### Changed

- **`models/config/account.py`（原 `accounts.py`）**：类名 `Accounts` → `Account`，字段 `root_id` → `admin_id`、`root_nickname` → `admin_nickname`
- **`models/config/plugin.py`**：`account` 字段类型 `Accounts` → `Account`，导入路径同步
- **`plugins/base_nodes/nodes/format_prompt.py`**：提示词块改用 `account.admin_id` / `account.admin_nickname`
- **`config.example.yaml`**：`account` 段的 `root_id` / `root_nickname` → `admin_id` / `admin_nickname`（此前模板已与模型脱节，照抄会直接 `ValidationError`）
- **`plugins/base_system_tools/README.md`**：删去「所有工具都没有管理员校验」段落（该责任移交给权限插件）

### Removed

- **`models/config/accounts.py`**：被 `account.py` 取代

### Note

- **验证**（真跑，非静态核对）：15 个真实注册工具名与权限表逐字比对（**无漏声明 / 无多余死条目 / 无重复**）；`Permission` 三种分支单测（`admin` 命中与落空、`white_list` 命中、`anyone`）；真实 `GraphPipeline` 端到端 —— 管理员 / 白名单 / 路人三种身份下，下游请求节点（站在 `call_llm` 位置）实际拿到的工具列表均符合权限表；`on_load` → 注册 `('pick_tools', 2)` → `on_close` 全流程无异常；根 `config.yaml` 与 `config.example.yaml` 均通过 `PluginConfig` 校验。
- **未验证**：插件整体在 NcatBot 运行时下的端到端对话未跑；未声明工具的 warning 未做去重（每次请求都打印，日志中重复属预期行为，按决定不处理）。
- **已知边界**：只覆盖「模型经 `call_llm` 请求工具」这条路径；若有节点或子插件直接 `await` 工具的 `ainvoke`，会绕过本插件。`enable: false` / 插件未加载 / 加载抛错时完全不过滤（全部工具放行），权限的强制力依赖本插件正常运行。

### Docs

- **README 更新至 0.9.6**：版本号 / 功能特性（工具权限控制）/ 目录树（新增 `tool_permission_manager/`）/ 内置子插件表（新增一行、修正 `base_system_tools` 行、五个 → 六个）/ 配置表（`account` 字段名）/ 项目状态新增本版段
- **CHANGELOG 新增本条目**

## [0.9.5] - 2026-10-01

> 📄 **子插件文档补齐（第二份）**：`base_system_tools` 新增 `README.md` —— 列清 5 个系统工具，并**明写当前的安全缺口**：所有工具都没有管理员校验，数据将完全公开，权限控制后续再加入。与 `meme_extension` 的隐私提示同一思路：把风险写在插件自己家门口。

### Added

- **`plugins/base_system_tools/README.md`（新增）**：列出该子插件提供的 5 个工具（`bash` / `read_file` / `read_image` / `replace` / `write`），并写明已知漏洞 —— 「所有工具都没有管理员校验，这意味着你的数据将被完全公开；后续将加入权限控制，粒度按实际需求而定」。

### Note

- **验证**：README 里的 5 个工具名与 `tools/__init__.py` 的导入 / `__all__` 以及各文件里 `@tool(args_schema=ToolSchema)` 的函数名逐一对得上（5/5，无遗漏无多余）；「无管理员校验」这条声明对照实际代码核对 —— `base_system_tools/` 全目录 `grep` `admin` / `permission` / `权限` 零命中，声明属实。
- **未验证**：权限控制尚未实现（README 里的「后续将加入」仍是计划，本版无任何代码改动）。

### Docs

- **README 更新至 0.9.5**：版本号 / 目录树（`base_system_tools` 行补 `+ README`）/ 内置子插件表（该行补 README 与「无管理员校验」提示）/ 项目状态新增本版段
- **CHANGELOG 新增本条目**

## [0.9.4] - 2026-10-01

> 🖼️ **image 段解析新增 `is_meme`，并把它收窄到 QQ 平台（同时更名）**：`ImageSegmentParser` → `QQImageSegmentParser`（文件 `image_parser.py` → `qq_image_parser.py`），`is_accept` 由 `isinstance(data, Image)` 收紧为 `isinstance(data, QQImage)`（`QQImage` 声明了 `sub_type: int = 0`，于是 `handle()` 里不再需要 `getattr` 兜底），`sub_type` 被消费成布尔 `is_meme` 交给模型，让 LLM 能区分「表情包」与「用户发的普通图片」；`meme_extension` 同时新增 README，写明「模型可能把普通图片误归档成表情包」的隐私风险。

### Added

- **`plugins/meme_extension/README.md`（新增）**：写明该子插件定位与风险 —— 「大模型可能会将用户发送的普通图片归档为表情包，导致用户隐私被泄露」。

### Changed

- **`plugins/base_parsers/segment_parsers/image_parser.py` → `qq_image_parser.py`（更名）**：类名 `ImageSegmentParser` → `QQImageSegmentParser`，`segment_parsers/__init__.py` 的导入与 `__all__`、`base_parsers/main.py` 的导入与 `register_segment_parser` 调用同步（注册顺序未变：At / Text / QQImage / File / Reply）；`is_accept` 由 `isinstance(data, Image)` 收紧为 `isinstance(data, QQImage)`，`handle()` 返回体由 `{image, size}` 变为 `{image, size, is_meme}` —— `is_meme = bool(data.sub_type)`（非 0 视为表情包，直接取属性，不再 `getattr`），`image` 仍为 `data.url or data.file`、`size` 仍为 `data.file_size`。
- **`plugins/base_system_tools/tools/bash.py`**：删除 `bash` 工具里那段描述「创建进程后报错会导致进程自己跑、工具却告诉 AI 报错」的 NOTE 注释（纯注释删改，行为不变）。

### Note

- **验证**（真对象，非静态核对）：用 `sub_type=1` / `sub_type=0` / 缺 `sub_type` 键 / 驼峰 `subType` / 缺 `url` / common `Image` / 直接构造 `QQImage` 七种形态跑 `QQImageSegmentParser` —— 前两种 → `is_meme: true` / `false`；缺键与驼峰 → `false`；缺 `url` 回退 `file`；common `Image` 被 `is_accept` 拒收；全程无日志输出。旧类名 `ImageSegmentParser` / 旧模块名 `image_parser` 在 `.py` 与文档中已无残留引用（`grep` 过 `.py` 与文档；CHANGELOG 0.8.0 条目里那处同名记录属史实，未改）。
- **已知限制一（平台耦合）**：解析器现在只接受 QQ 平台的 `QQImage` —— 若哪天换非 QQ 适配器（lark / ai / …）跑本插件，image 段会无人 accept：`BaseParserChain.dispatch` 返回 `DispatchResult(is_handled=False)`（`result` 默认 `None`），`parse_message` 会把这个 `None` 塞进 `segments`，`format_input` 于是输出一条 `null`（丢图，不报错）。QQ 专用插件下这是有意的耦合，本仓库也已有先例（`adapters/event_adapter.py` 直接用 `ncatbot.types.napcat.message`）。
- **已知限制二（静默 `false`）**：`QQImage.from_dict` 不做键名转换，payload 若用驼峰 `subType`，`sub_type` 会保持默认 `0` → `is_meme` 静默为 `false`；上游报文若压根不带 `sub_type`，结果同样是静默 `false`（属性有默认值 0，`hasattr` 判断不出「没发」—— 本版按「已确认不会缺」去掉日志，若日后要恢复这个信号，应改用 `"sub_type" not in data.model_fields_set`）。真机上若发现表情包识别不出来，先确认 NapCat 发的是哪种键名 / 到底发没发。
- **未验证**：`is_meme` 进入提示词后模型的识别效果，以及 NapCat 真机上 `sub_type` 的实际取值分布（本轮靠构造 payload 验证，没有真实报文）。

### Docs

- **README 更新至 0.9.4**：版本号 / 多类型消息段（`Image` → `{image, size, is_meme}`，注明解析器只收 `QQImage`）/ 目录树与内置子插件表（`meme_extension` 补 README）/ 项目状态新增本版段
- **CHANGELOG 新增本条目**

## [0.9.3] - 2026-10-01

> 📦 **把三个「直接 import 却靠传递依赖混进来」的包正式声明**：`langchain-core` / `pydantic` / `pyyaml` —— 0.9.2 的扫描把这三个点出来了，它们目前分别是 `ncatbot`（pydantic / PyYAML）与 `langgraph` / `langchain-openai`（langchain-core）的传递依赖，上游一旦改依赖树本插件就会在导入期炸。`pip_dependencies` 10 → 13 项。

### Fixed

- **`manifest.toml` 补 `langchain-core = ">=1.6.5"`**：`core/registry.py` / `core/tool_registry.py` 与各子插件用 `@tool`，`models/graph_runtime_context.py` 等用 `BaseMessage` / `BaseChatModel`
- **`manifest.toml` 补 `pydantic = ">=2.13.5"`**：配置层（`models/config/` 全套的 `BaseModel` / `Field` / `model_validator`）与各工具的参数 schema 都直接依赖它
- **`manifest.toml` 补 `pyyaml = ">=6.0.3"`**：`core/plugin_loader.py` 用 `yaml.safe_load` 读子插件的 `config.yaml`

### Note

- 三者的版本下限都取当前环境实测版本（`langchain-core` 1.6.5 / `pydantic` 2.13.5 / `PyYAML` 6.0.3），与清单里其余依赖「下限 = 实测版本」的写法一致
- **验证**：`ast` 扫全仓顶层绝对 import（排除 stdlib 与本地包）对照 `pip_dependencies`，**未声明项归零**（0.9.2 扫描时还剩这三个）；`manifest.toml` 经 `tomllib` 解析通过（0.9.3 / 13 项依赖）
- **未验证**：插件整体 `on_load` 与各子插件在 NcatBot 运行时下的端到端调用未跑（延续 0.9.0 的未验证项）

### Docs

- **README 更新至 0.9.3**：版本号 / 安装依赖列表与依赖表新增 `langchain-core` / `pydantic` / `pyyaml` / 项目状态新增本版段
- **CHANGELOG 新增本条目**

## [0.9.2] - 2026-10-01

> 📦 **补齐 `aiofiles` 依赖声明**：`base_system_tools` 的 `write` / `replace` 两个工具一直在用 `aiofiles` 异步写盘，但 `manifest.toml` 从未声明它 —— 开发机上恰好装着所以没暴露；干净环境（或 `plugin.auto_install_pip_deps` 自动装依赖时）会在导入 `base_system_tools` 时 `ModuleNotFoundError: aiofiles`。

### Fixed

- **`manifest.toml` 补 `aiofiles = ">=24.1.0"`**（`pip_dependencies` 9 → 10）：`plugins/base_system_tools/tools/write.py` 与 `replace.py` 都以 `import aiofiles` + `async with aiofiles.open(...)` 写文件，而 `base_system_tools/main.py` 在 `on_load` 里 `from .tools import write, replace, …` —— 缺包时该子插件整体加载失败，并因 0.9.0 的 NOTE（`load_all()` 一处抛错即中断整批）连带排在它后面的子插件也不再加载。

### Note

- **验证**：`ast` 扫全仓顶层绝对 import 比对 `pip_dependencies`，`aiofiles` 已消除；两个工具端到端跑通 —— 写入落盘、全量替换、`count=1` 只替换第一处、`encoding=gbk` 读写、目标不可写时返回 `fail(...)`（`FileNotFoundError`）而不抛异常。
- **未验证**：`base_system_tools` 在 NcatBot 运行时下的工具端到端调用未跑。
- **仍缺声明（本次未动）**：扫描同时发现 `langchain_core`（`core/registry.py` / `core/tool_registry.py` / `models/graph_runtime_context.py` 等）、`pydantic`（`models/config/` 等）、`yaml`（`core/plugin_loader.py`）也是直接 import 但未在 `manifest.toml` 声明，目前靠 `ncatbot` / `langgraph` / `langchain-openai` 的传递依赖进来。

### Docs

- **README 更新至 0.9.2**：版本号 / 安装依赖列表与依赖表新增 `aiofiles` / 项目状态新增本版段
- **CHANGELOG 新增本条目**

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