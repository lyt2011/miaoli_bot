修复孤儿工具返回 —— 「有返回没请求」。

`fix_orphan_tool_message` 节点挂在 `on_before_request`（`priority=NORMAL+2`），删掉那些「找不到发起它的 `tool_calls`」的 `ToolMessage`。

只产出定向删除增量（`[RemoveMessage(id=m.id) for m in orphans]`），比整表重写省；没有孤儿时直接返回 `None`，不写任何增量。

与 `pending_tool_fixer` 成对：那个治「有请求没返回」。两者互不依赖、各自独立判断，谁先跑都不影响结果。触发场景是上一轮工具执行中途异常／并发冲突导致消息形状坏掉，此后每轮请求模型都会 `400 insufficient tool messages following tool_calls`。
