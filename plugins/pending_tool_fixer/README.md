修复悬空的工具调用 —— 「有请求没返回」。

`fix_pending_tool_call` 节点挂在 `ON_REQUEST`（`priority=MEDIUM`），先收集消息表里所有 `ToolMessage.tool_call_id` 作为「已应答」集合，再逐个 `AIMessage` 检查它的 `tool_calls` 与 `invalid_tool_calls`，没有对应返回的补一条合成 `ToolMessage`，直接插在该 `AIMessage` 之后，最后返回 `Overwrite` 整表替换。

合成结果固定为 `id = f"auto-fix: {tool_call_id}"`、`status = "error"`、`name` 取原调用名；正文按调用来源分两种，常量在 `consts/fix_texts.py`：

| 来源 | 正文 |
|---|---|
| `tool_calls`（schema 正确，只是没跑完）| `COMMON_FIX_TEXT`：`该工具被意外中断，请根据实际状态决定是否需要重新调用工具` |
| `invalid_tool_calls`（参数不是合法 JSON，压根没调成）| `INVALID_FIX_TEXT`：`无法解析该工具的参数 schema，工具未被调用，请使用正确的 schema 以调用工具` |

历史本就合法时（`repaired` 与 `messages` 等长）直接返回 `None` —— 这条守卫是必需的，否则每轮都会把整张消息表写进 `checkpoint_writes`。

## 无配置

不读 `config.yaml`，节点每次加载都注册，没有 `enable` 开关（旧的 `enable` / `fix_message` 两项在 0.51.0 移除）。要停就在主包配置的 `sub_plugin.load_from` 里去掉这个目录。文案改 `consts/fix_texts.py`。

与 `orphan_tool_fixer` 成对：那个治「有返回没请求」。两者互不依赖、各自独立判断，谁先跑都不影响结果（增量折叠对形态不敏感，定向删除与整表替换可以任意顺序组合）。触发场景是上一轮工具执行中途异常／并发冲突导致消息形状坏掉，此后每轮请求模型都会 `400 insufficient tool messages following tool_calls`。
