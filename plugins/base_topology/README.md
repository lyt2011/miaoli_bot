图的基础拓扑 —— edgeless 下「下一个事件是谁」的默认答案。

框架的 `wire()` 只挂 11 个事件节点和一条入口边，不定义任何顺序；顺序由处理器主动返回跳转指令决定。本插件就是那个默认跳转：**一个事件一个节点文件**，每个只返回一条 `Goto`。

| 节点 | 下一跳 |
| --- | --- |
| `on_agent_start` | `ON_TURN_START` |
| `on_turn_start` | `ON_BEFORE_COMPACT` |
| `on_before_compact` | `ON_BEFORE_REQUEST`（默认不压缩） |
| `on_compact` | `ON_AFTER_COMPACT` |
| `on_after_compact` | `ON_TURN_START`（重走一轮） |
| `on_before_request` | `ON_REQUEST` |
| `on_request` | `ON_AFTER_REQUEST` |
| `on_after_request` | 末条消息带 `tool_calls` → `ON_TOOL_CALLING`，否则 → `ON_TURN_END` |
| `on_tool_calling` | `ON_TURN_START`（重走一轮） |
| `on_turn_end` | `ON_AGENT_END` |
| `on_agent_end` | `END` |

全部注册在**最低优先级** `MINIMUM`，所以任何子插件挂在任何更高档位都能抢在默认跳转之前改道或叫停。

## 压缩三段

`ON_BEFORE_COMPACT` / `ON_COMPACT` / `ON_AFTER_COMPACT` 是 0.22.0 新增的三个事件，把压缩从 `on_before_request` 里的一个 `if` 拆成图上三个有名字的环节：

```
ON_TURN_START
  → ON_BEFORE_COMPACT   守卫判阈值（context_compactor 的 should_compact，priority=NORMAL）
      ├─ 不需要压缩 → ON_BEFORE_REQUEST
      └─ 需要压缩   → ON_COMPACT   真压缩（compact，Overwrite 替换 messages）
                        → ON_AFTER_COMPACT
                        → 跳回 ON_TURN_START
```

默认路径（本插件提供）是**不压缩**：`on_before_compact` 直接跳 `ON_BEFORE_REQUEST`。装了 `context_compactor` 之后，它的守卫挂在更高优先级（`NORMAL`），先跑并返回 `Goto`，默认跳转就被短路。

`on_after_compact` 跳回 `ON_TURN_START` 而不是往下走，是为了让压缩后的这一轮重新经过完整流程 —— 但这也意味着**守卫会再跑一次**。`context_compactor` 的 `should_compact` 靠「`messages[-1].content` 里有没有 `compaction` 字样」拦截二次压缩（命中就 `Abort`），否则压缩后 token 仍超限时会无限循环到 `GraphRecursionError`。

## 注意事项

- **图没有它跑不起来**：所有处理器都只返回增量 dict 时，节点就没有下一跳，langgraph 视为终点 —— 图在第一个事件后就静默结束，`final_answer` 缺失。特别是**某个事件一个处理器都没有**时（`wire()` 挂了节点但没人 `register`），那个节点会静默返回空 dict，图在那里就断了。
- **`on_tool_calling` 回到 `ON_TURN_START` 而不是 `ON_BEFORE_REQUEST`**（旧静态边的走法）：每轮工具调用会重走一遍「轮开始」，`build_client` 会重建一次 `Chat[OI]`（幂等，代价是多一次对象构造与配置查找）。
- `config.yaml` 的 `enable` 为 `false` 时不注册任何节点，等同于图不可运行。
