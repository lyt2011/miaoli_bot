图管线的基础节点。

| 节点 | 事件 | 优先级 | 作用 |
| --- | --- | --- | --- |
| `build_client` | `on_turn_start` | `NORMAL` | 按根配置里的供应商 / 模型名建 LLM 客户端，写进 `runtime.context["client"]` |
| `compact_if_need` | `on_before_request` | `HIGH` | 历史 token 总量过门槛才压：`get_compaction_range` 求出区间 → `core.compact.compact_now` 压缩 → `Overwrite` 拼回区间外原文 |
| `call_llm` | `on_request` | `NORMAL` | 绑工具后请求模型，返回的 `AIMessage` 追加进 `messages` |
| `invoke_tools` | `on_tool_calling` | `NORMAL` | 用 `ToolNode` 执行模型请求的工具，`ToolMessage` 追加进 `messages` |
| `output_checker` | `on_agent_end` | `LOWEST` | 检查 `messages[-1]` 的类型：不是 `AIMessage` 就 `Abort`（空列表 / `ToolMessage` / `HumanMessage` / 未知类型四种理由） |

## 压缩节点

`compact_if_need` 挂在 `ON_BEFORE_REQUEST` 的 `HIGH`(100)，是这个事件里跑得最早的处理器 —— 此时 `messages` 还没被 `time_inject`（`NORMAL+2`）/ `build_prompt`（`NORMAL+1`）改过，压缩看到的就是上一轮落盘的历史。

两步都是短路优先：

1. **门槛**：`sum(estimate_message_tokens(message) for message in messages) < context_window - max_tokens` 直接返回 `None`，不发请求、不写增量。`context_window` / `max_tokens` 取自 `api.get_model_info()`（`model.model_dump()`，按字典键取）。
2. **区间**：`get_compaction_range(messages)` 返回 `None`（没有可压的段落）也直接返回 `None`。

过了两道之后把 `messages[p_start:p_end + 1]` 交给 `compact_now(messages, client, 20000)`，返回 `CompactFailed` 时只打日志、返回 `None`（原历史保持不动）；`CompactSuccess` 时按

```python
[*messages[:p_start], HumanMessage(result.summary), *result.messages_after, *messages[p_end + 1:]]
```

拼成新列表用 `Overwrite` 整体替换。

区间保证：`SystemMessage` 不进区间；区间右端停在最后一段连续 `HumanMessage` 之前（群聊里连发的用户原话不会被压掉）；区间左端不落 `ToolMessage`、右端不回退到带 `tool_calls` 的 `AIMessage`（不拆工具组、不留孤儿工具结果）；可用长度不足两条时返回 `None`。

`output_checker` 用 `LOWEST`（-100）而不是 `MINIMUM`（-9999）：`MINIMUM` 是 `default_routing` 给每个事件挂兜底跳转用的优先级，`on_agent_end` 的 `Goto(END)` 就挂在那里。优先级数值大的先跑，而 `_dispatch` 一遇到 `Goto` 就返回 `Command` 短路掉本事件剩下的处理器，所以 `Abort` 必须先于兜底下手；`LOWEST` 的 -100 严格高于 `MINIMUM` 的 -9999，这一点不依赖注册顺序。检查通过时处理器返回 `None`，兜底照常接上 `Goto(END)` 结束图。
