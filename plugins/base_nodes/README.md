图管线的基础节点。

| 节点 | 事件 | 优先级 | 作用 |
| --- | --- | --- | --- |
| `format_input` | `on_agent_start` | `NORMAL` | 把 `event` + `segments` 序列化成 `HumanMessage` 追加进 `messages` |
| `build_client` | `on_turn_start` | `NORMAL` | 按 state 里的供应商 / 模型名建 `Chat[OI]` 写进 `runtime.context["client"]` |
| `compact` | `on_request` | `NORMAL+1` | token 超窗时把历史压成一条 `<compaction>` 摘要，整表替换 `messages` |
| `call_llm` | `on_request` | `NORMAL` | 绑工具后请求模型，返回的 `AIMessage` 追加进 `messages` |
| `invoke_tools` | `on_tool_calling` | `NORMAL` | 用 `ToolNode` 执行模型请求的工具，`ToolMessage` 追加进 `messages` |
| `attach_image` | `on_tool_calling` | `NORMAL-1` | 把工具结果里的图片块挪成一条 `HumanMessage` |
| `latest_to_answer` | `on_agent_end` | `NORMAL` | 取 `messages[-1]` 的正文写进 `final_answer` |

注意 `compact` 必须排在 `call_llm` 之前、`invoke_tools` 必须排在 `attach_image` 之前，靠优先级保证。
