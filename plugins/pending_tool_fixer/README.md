修复悬空的工具调用 —— 「有请求没返回」。

`fix_pending_tool_call` 节点挂在 `on_before_request`（`priority=NORMAL+3`），发现存在发起但不存在返回的 `tool_call` 时，在每个悬空 `AIMessage` 之后插一条合成的 `ToolMessage`（`status="error"`、`id=f"auto-fix: {tool_call_id}"`），返回 `Overwrite` 整表替换。

历史本就合法时（`fixed == 0`）直接返回 `None` —— 这条守卫是必需的，否则每轮都会把整张消息表写进 `checkpoint_writes`。

## 配置

```yaml
enable: true
fix_message: "The tool was unexpectedly interrupted, and the results have been lost. Please confirm the status before proceeding to the next step."
```

`fix_message` 是合成 `ToolMessage` 的正文，按需改成你想要的提示（上为仓库里的默认值）。

与 `orphan_tool_fixer` 成对：那个治「有返回没请求」。两者互不依赖、各自独立判断，谁先跑都不影响结果。触发场景是上一轮工具执行中途异常／并发冲突导致消息形状坏掉，此后每轮请求模型都会 `400 insufficient tool messages following tool_calls`。
