修复工具结果里的附件 —— 某些模型不接受 `tool` 消息携带多模态块，直接请求会 `400`。

`fix_tool_attachment` 节点挂在 `on_tool_calling`（`priority=NORMAL-2`），把带附件的 `ToolMessage` 改成纯文本（正文换成 `replace_text`），再把原来的多模态块原样挪进紧跟其后的一条 `HumanMessage`（`id=f"image-{tool_call_id}"`），返回 `Overwrite` 整表替换。文本内容不丢，只是换了个角色承载。

只对 `models` 里声明的模型生效；没有改动时（`is_changed == False`）直接返回 `None` —— 这条守卫是必需的，否则每轮都会把整张消息表写进 `checkpoint_writes`。

## 配置

```yaml
enable: true
models:
  - "deepseek/deepseek-flash"
  - "deepseek-flash"
replace_text: "该工具产生的附件已被添加进入上下文中。"
```

- `models`：生效的模型名单，两种写法都认 —— `<provider>/<model>`（如 `deepseek/deepseek-flash`）与 `<model>`（如 `deepseek-flash`），命中任一即生效。**留空 = 对所有模型生效**。
- `replace_text`：替换后 `ToolMessage` 的正文。

## 与 `base_nodes` 的关系

本节点是从 `base_nodes` 的 `attach_image` 移植过来的，区别只在「模型门控」与「`id` 稳定性」两点 —— `attach_image` 无条件生效，且新建的 `HumanMessage` 不带 `id`。移植后 `base_nodes/nodes/_attach_image.py` 已删除，两处不要同时启用，否则后跑的那个会扫不到附件（前一个已把 `ToolMessage.content` 换成字符串）。

## ⚠️ 已知问题（待修复，见 CHANGELOG 的 Future）

附件搬移逻辑存在**两个独立缺陷**，叠加后会产出**非法消息结构**，把会话**永久损坏**。当前建议先 `enable: false` 停用。

### 缺陷 1：`is_block_content` 判定过宽

`utils/guards.py:26-28`：

```python
def is_block_content(content: Any) -> bool:
	"""判断是否为块列表（非字符串）"""
	return isinstance(content, list)
```

任何 `list` 都被当成「附件」。而 MCP 工具返回的 `[{"type": "text", …}]` 是**纯文本块**、不含任何多模态内容，同样被误判 → 真实结果被换成 `replace_text` 占位符，再被搬进一条 `HumanMessage`。

### 缺陷 2：`pending` 的 flush 时机错误

`nodes/fix_attachment.py:35-44` 在遇到**任何非 target 消息**时就把 `pending` 倒出，而此刻 `message` 完全可能只是**另一条 `ToolMessage`**：

```python
if not is_target_message(message):
	if pending:
		replaced.extend(pending)   # ← 倒早了
		pending.clear()
```

同一批工具里**只有一部分**被改写时，`HumanMessage` 就会插进 `ToolMessage` 序列**中间**，产出 `AI(tool_calls) → TM, Human, TM`。

### 后果

`AI(tool_calls)` 之后的 `ToolMessage` **必须连续**。结构被打断后有两种走向，都很难发现：

- **硬崩**：模型直接 `400`（`deepseek-flash` 实测报 `insufficient tool messages following tool_calls message`）。坏结构已经落进 `checkpoint_blobs`、**不会自愈**，该会话从此**每轮必崩**
- **静默失效**：模型返回 `200`，但把附件当成「没提供图片」，附件白给

### 临时规避

`enable: false`。关掉后 `fix_tool_attachment` 不再注册，`on_tool_calling` 上只剩 `invoke_tools(0)`。

### 修复方向

1. **收窄判定** —— 只把含**真正多模态块**的 `list` 当附件（`TEXT_BLOCK_TYPES = {"text", "text_delta"}`），纯文本块列表直接放过
2. **改 flush 时机** —— `pending` 只在遇到**非 `ToolMessage`** 时才倒出，整段连续 `ToolMessage` 的附件统一在**段末**插入，保证「`AI(tool_calls)` 之后 `ToolMessage` 连续」这一不变式
3. 可选：搬移时**只移走非文本块**、文本留在 `ToolMessage` 里（现在整块换成占位符，信息浪费）
4. 可选：写回前做**结构自检**，不合法就 `return None` —— 坏结构的代价是永久损坏会话，宁可不动

### 补充：插件并非无用

实测存在一类模型：能接受 `tool` 消息携带图片，但**静默忽略图片内容**（返回 `200`，回答却是「我看不到图片」）。对这类模型，把附件搬进 `HumanMessage` 是唯一让模型看到附件的途径。

所以修复方向是**修好它**而不是删掉它 —— 对另一类模型（如 `deepseek-flash`）它才是有害的，靠 `models` 门控或 `enable` 开关区分即可。
