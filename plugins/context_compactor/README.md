# Context Compactor

上下文压缩子插件：当消息接近模型上下文窗口时，调一次模型把历史总结成一段摘要，并用「摘要 + 最近若干条消息」整体替换 `messages`。

替代原 `base_nodes` 里的 `_compact.py`。

## 工作流程

`compact` 节点挂在 `on_before_request`（`priority=NORMAL`）：

1. **算 token** —— 按 `calculate.mode` 选公式（见下）
2. **判是否要压** —— `usage_tokens + max_tokens < context_window` 时不压，直接返回 `None`（不写任何增量）
3. **压** —— 请求体是 `[SystemMessage(system_prompt), *messages, HumanMessage(prompt)]`，`system_prompt` 不存在时省略
4. **替换** —— 返回 `Overwrite([HumanMessage("<compaction>摘要</compaction>"), *最近 N 条])`

摘要以 `<compaction>...</compaction>` 包裹后作为 `HumanMessage` 落在 `messages[0]`。

## 配置

```yaml
enable: true
encoding: "utf-8"
prompt_file: "/sdcard/Ncatbot_QQ/plugins/miaoli_bot/plugins/context_compactor/data/compact_prompt.md"
keep_count: 5
calculate:
  mode: "base"
  encoder: "o200k_base"
```

| 键 | 说明 |
| --- | --- |
| `enable` | 关闭时不注册节点，即不压缩 |
| `encoding` | 读 `prompt_file` 用的编码 |
| `prompt_file` | 压缩提示词文件，**绝对路径** |
| `keep_count` | 压缩后保留多少条最近消息 |

### 保留规则

`keep_recent_messages` 从后往前收，只对 `HumanMessage` / `AIMessage` / `SystemMessage` 计数 —— **`ToolMessage` 不占配额**，避免把「有请求没返回」的 `tool_calls` 切开。倒序收集保证了尾部连续。

## token 计算

`calculate.mode` 两选一：

| `mode` | 实现 | 说明 |
| --- | --- | --- |
| `base` | `base_calculate` | 不依赖 `tiktoken` 的兜底估算，`字符数 × 0.7` |
| `tiktoken` | `tiktoken_calculate` | 精确计数，需同时填 `encoder` |

`mode: "tiktoken"` 时 `encoder` 必填（`o200k_base` / `cl100k_base`），由 `CalculateConfig` 的 `model_validator` 校验。

`base` 是**故意粗糙**的兜底：`tiktoken` 首次使用要下载编码文件，离线环境会失败。系数 `0.7` 取的是「宁可早压也不溢出」—— 实测真实语料约 `0.55` tok/字（消息里大量 JSON 事件体），纯中文约 `0.9`。

## 图片处理

多模态 `content` 里的图片不按 base64 字符数计，而是解出宽高后折算成占位符：

```
占位符个数 = int(sqrt(min(宽,1920) × min(高,1080)))
```

占位符是汉字 `图` —— 在 `o200k_base` 里**严格 1 字符 = 1 token**（ASCII 会被 BPE 合并，实测 `'a'×1000 → 125 token`，故不能用）。

图片解不开（损坏 / 非图片 / 非 base64）时统一按 `1000` 计，不抛异常。

## 注意事项

- **`prompt_file` 用绝对路径**，不再依赖进程 CWD
- **`on_close` 会 `drop` 两个 `SHARE_STORE` 键**，插件重载不会残留旧配置
- **摘要质量取决于 `prompt_file`** —— 仓库默认提示词要求「绝对时间表述 + 第三人称」，实际效果受对话内容影响（有明确时间戳的对话遵守得更好）
- **坏图片会让压缩一并失败**：压缩请求带全量 `messages`，若其中含 API 拒绝的图片，压缩和 `call_llm` 会同时 `400`
