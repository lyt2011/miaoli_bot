图的基础拓扑 —— edgeless 下「下一个事件是谁」的默认答案。

框架的 `wire()` 只挂 8 个事件节点和一条入口边，不定义任何顺序；顺序由处理器主动返回跳转指令决定。本插件就是那个默认跳转：**一个事件一个节点文件**，每个只返回一条 `Goto`。

| 节点 | 下一跳 |
| --- | --- |
| `on_agent_start` | `ON_TURN_START` |
| `on_turn_start` | `ON_BEFORE_REQUEST` |
| `on_before_request` | `ON_REQUEST` |
| `on_request` | `ON_AFTER_REQUEST` |
| `on_after_request` | 末条消息带 `tool_calls` → `ON_TOOL_CALLING`，否则 → `ON_TURN_END` |
| `on_tool_calling` | `ON_TURN_START`（重走一轮） |
| `on_turn_end` | `ON_AGENT_END` |
| `on_agent_end` | `END` |

全部注册在**最低优先级** `MINIMUM`，所以任何子插件挂在任何更高档位都能抢在默认跳转之前改道或叫停。

## 注意事项

- **图没有它跑不起来**：所有处理器都只返回增量 dict 时，节点就没有下一跳，langgraph 视为终点 —— 图在第一个事件后就静默结束，`final_answer` 缺失。
- **`on_tool_calling` 回到 `ON_TURN_START` 而不是 `ON_BEFORE_REQUEST`**（旧静态边的走法）：每轮工具调用会重走一遍「轮开始」，`build_client` 会重建一次 `Chat[OI]`（幂等，代价是多一次对象构造与配置查找）。
- `config.yaml` 的 `enable` 为 `false` 时不注册任何节点，等同于图不可运行。
