图管线的基础节点。

| 节点 | 事件 | 优先级 | 作用 |
| --- | --- | --- | --- |
| `build_client` | `on_turn_start` | `NORMAL` | 按根配置里的供应商 / 模型名建 LLM 客户端，写进 `runtime.context["client"]` |
| `call_llm` | `on_request` | `NORMAL` | 绑工具后请求模型，返回的 `AIMessage` 追加进 `messages` |
| `invoke_tools` | `on_tool_calling` | `NORMAL` | 用 `ToolNode` 执行模型请求的工具，`ToolMessage` 追加进 `messages` |
| `output_checker` | `on_agent_end` | `LOWEST` | 检查 `messages[-1]` 的类型：不是 `AIMessage` 就 `Abort`（空列表 / `ToolMessage` / `HumanMessage` / 未知类型四种理由） |

`output_checker` 用 `LOWEST`（-100）而不是 `MINIMUM`（-9999）：`MINIMUM` 是 `default_routing` 给每个事件挂兜底跳转用的优先级，`on_agent_end` 的 `Goto(END)` 就挂在那里。优先级数值大的先跑，而 `_dispatch` 一遇到 `Goto` 就返回 `Command` 短路掉本事件剩下的处理器，所以 `Abort` 必须先于兜底下手；`LOWEST` 的 -100 严格高于 `MINIMUM` 的 -9999，这一点不依赖注册顺序。检查通过时处理器返回 `None`，兜底照常接上 `Goto(END)` 结束图。
