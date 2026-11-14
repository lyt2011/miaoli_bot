# Base Compact

把一段消息压成摘要的**库型子插件** —— 没有节点、不注册任何事件，只对外提供函数与结果类型。

## 为什么单独成插件

压缩的三样东西属于同一层：**提示词**（`consts/prompt.py` 的 `COMPACT_PROMPT`）、**估算与剪枝**（`utils/`）、**编排**（`core/compact_now.py`）。

提示词是这份能力里唯一不可替换的资产，而主包不持有任何提示词 —— 所以它跟着压缩一起搬出来。谁想换一套压缩策略，改这个插件就够了，不用动主包。

## 谁在用

只有 `base_nodes` 的 `compact_if_need`（`ON_BEFORE_REQUEST`，`priority=HIGH`）。它自己决定**什么时候压**（上下文是否超过 `context_window - max_tokens`）、**压哪一段**（`get_compaction_range`）、**留多少 token 预算**，然后调用 `compact_now`。

`base_nodes/metadata.toml` 里声明了 `dependences = [base_compact]` —— 加载顺序靠这个拓扑排序，不靠目录名。

## 目录

| 路径 | 内容 |
|---|---|
| `api/` | 对外门面：把 `consts/` `core/` `runtimes/` `utils/` 四层的 19 个公有符号全部转出（不藏私有以外的东西），组间按模块名、组内按名字升序 |
| `core/` | 编排 `compact_now`、逐条渲染 `ChatHistory` |
| `runtimes/` | 两个结果类型 `CompactSuccess` / `CompactFailed` |
| `utils/` | 纯函数：token 估算、内容与 tool_calls 提取、剪枝、截断 |
| `consts/` | 压缩提示词、摘要标签、截断/工具调用标签模板、token 常数 |

## 调用链

```
messages ──prune_messages──▶ tokens_before / tokens_after / 剪枝后副本
   │
   └─ChatHistory.from_messages─▶ ["[User]: …", "[Assistant]: …", …]
                                    │
                                    └─truncate_content_if_need─▶ 拼成 history
                                                                   │
                                      COMPACT_PROMPT + history ──▶ client.ainvoke
                                                                   │
                                                          summary ──▶ CompactSuccess
```

`prune_messages` 只影响**返回值里的 `tokens_after` / `messages_after`**，喂给模型的是 `ChatHistory` 渲染出来的全文 —— 剪枝是给调用方回写上下文用的，不是给模型看的。

## `prune_messages` 的三条不剪

按 token 预算从**最旧**的一端删，但以下永不删：

- `SystemMessage`
- `ToolMessage`
- 带 `tool_calls` 或 `invalid_tool_calls` 的 `AIMessage`

删掉 `ToolMessage` 或带 `tool_calls` 的 `AIMessage` 会让上下文里出现悬空引用（有 `tool_call_id` 却找不到对应调用），供应商直接 400。

返回 `(剪枝前 tokens, 剪枝后 tokens, 剪枝后的消息副本)`，**不改入参**。

## 结果类型

| 类型 | 何时返回 |
|---|---|
| `CompactFailed(reason, exception=None)` | 入参为空，或模型返回空摘要 |
| `CompactSuccess(summary, used_time, tokens_before, tokens_after, messages_before, messages_after)` | 正常完成 |

`summary` 已用 `<summary>` 标签包好（`consts/tags.py` 的 `SUMMARY_TAG`），调用方直接当 `HumanMessage` 塞回去即可。

**失败不是异常**，是返回值 —— 压缩失败不该让整轮对话炸掉，调用方只记一条日志就继续。

## token 估算的精度

`estimate_text_tokens` 是 `len(text) * 0.47`，`estimate_content_tokens` 对图片块按 `1440` 兜底，**都不解析 base64**。

这意味着估算值只是量级正确，用于「该不该压」的判断足够，用于精确计费不够。所有估算函数返回**未取整的 float**，取整与舍入由调用方决定。

## 已知短板

- **`retain_tokens` 由调用方硬编码**：`base_nodes/nodes/compact.py` 里写死 `20000`，还没想好配置放哪。
- **摘要长度靠提示词自觉**：提示词要求「尽量控制在 1500 字以内」，但没有程序侧校验，模型写超了也照收。
- **压缩一次只看一个区间**：超出预算时不会反复压，剪枝后仍然超预算也不会追加处理。
