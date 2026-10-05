图管线的基础节点。

| 节点 | 事件 | 优先级 | 作用 |
| --- | --- | --- | --- |
| `format_input` | `on_agent_start` | `NORMAL` | 把 `event` + `segments` 序列化成 `HumanMessage` 追加进 `messages` |
| `build_client` | `on_turn_start` | `NORMAL` | 按 state 里的供应商 / 模型名建 `Chat[OI]` 写进 `runtime.context["client"]` |
| `call_llm` | `on_request` | `NORMAL` | 绑工具后请求模型，返回的 `AIMessage` 追加进 `messages` |
| `invoke_tools` | `on_tool_calling` | `NORMAL` | 用 `ToolNode` 执行模型请求的工具，`ToolMessage` 追加进 `messages` |
| `latest_to_answer` | `on_agent_end` | `NORMAL` | 取 `messages[-1]` 的正文写进 `final_answer` |
