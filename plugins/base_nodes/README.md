图管线的基础节点。

| 节点 | 事件 | 优先级 | 作用 |
| --- | --- | --- | --- |
| `build_client` | `on_turn_start` | `NORMAL` | 按根配置里的供应商 / 模型名建 LLM 客户端，写进 `runtime.context["client"]` |
| `call_llm` | `on_request` | `NORMAL` | 绑工具后请求模型，返回的 `AIMessage` 追加进 `messages` |
| `invoke_tools` | `on_tool_calling` | `NORMAL` | 用 `ToolNode` 执行模型请求的工具，`ToolMessage` 追加进 `messages` |
| `output_checker` | `on_agent_end` | `LOW` | 检查 `messages[-1]` 的类型：不是 `AIMessage` 就 `Abort`（空列表 / `ToolMessage` / `HumanMessage` / 未知类型四种理由） |

`output_checker` 用 `LOW`（-10）而不是 `MINIMUM`（-9999）：`default_routing` 的 `on_agent_end` 兜底在 `MINIMUM`，`LOW` 严格高于它，`Abort` 才有机会抢在 `Goto(END)` 之前 —— 不依赖注册顺序。
