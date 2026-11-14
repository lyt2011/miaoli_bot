# Base LLM

带重试的模型调用入口 —— **库里没有节点**，不注册任何事件，只提供 `call_llm` 一个函数。

## 为什么单独成插件

主包里「怎么发一次模型请求」这件事被拆成了两处：`api.build_client` 建客户端，各处自己 `await client.ainvoke(messages)`。一旦要加退避、要按异常类型分流、要统计失败次数，每个调用点都得抄一遍。

`call_llm` 把这一段收成唯一入口：谁要调模型就调它，重试策略只在这里长。它是纯逻辑，跟图、跟事件、跟会话都无关，所以放主包只是历史原因，搬出来才能独立演进。

## 目录

| 路径 | 内容 |
|---|---|
| `api/` | 对外门面：`call_llm` / `is_retriable` / `MaxRetryLimitError` |
| `core/` | 重试循环本体 |
| `utils/` | 异常可重试判据（**目前恒 `False`**） |
| `errors/` | 尝试次数耗尽时抛的异常，继承主包的 `BaseBotError` |

## 对外契约

```python
async def call_llm(
	messages : List[BaseMessage],
	client   : BaseChatModel,
	*,
	max_retry: int = 0,
) -> Tuple[int, List[Exception], AIMessage]
```

返回 `(尝试次数, 途中出现的所有错误, 最终回复)` —— 成功那次也可能已经失败过几次，`exceptions` 把这些都留着，便于调用方记录或上报。

失败抛 `MaxRetryLimitError(exceptions=..., times=...)`，`from` 挂着最后一次的原始异常。

## `max_retry` 是总尝试次数，不是重试次数

```
max_retry=0  →  第 1 次失败就抛（times=1）
max_retry=1  →  第 1 次失败就抛（times=1）       ← 与 0 等价
max_retry=3  →  最多调 3 次，第 3 次失败抛（times=3）
```

判据是 `cur_times >= max_retry`，`cur_times` 在请求**之前**自增。所以 `0` 和 `1` 行为完全一致，语义上取 `0` 表示「不打算重试」。

## `is_retriable` 恒 False 意味着什么

现在**一次都不会重试**。任何异常进 `except` 后先 `exceptions.append`，接着 `cur_times >= max_retry` 或 `not is_retriable(exc)` 任一为真就抛 —— 后者永远为真，所以 `max_retry` 目前是死参数。

真正接进去时要决定的是：哪些异常值得重试。至少得排除 `400` 类（消息形状坏、参数错、鉴权失败），这些重试一百次也一样；超时、限流、`5xx` 才有意义。这是有意留的桩，不是漏写。

## 现状：零调用点

`base_nodes/nodes/call_llm.py`（节点）与 `base_compact/core/compact_now.py` 目前都还是直接 `await client.ainvoke(...)`。

节点那个 `call_llm` 与本插件的 `call_llm` **是两个不同的东西**：节点签名是 `(state, runtime)`，本插件是 `(messages, client, *, max_retry)`。搬过来只是把能力放到了能独立演进的位置，接线还没做。

## 已知短板

- **`is_retriable` 恒 `False`**，重试机制整个是空转的（见上）。
- **没有退避**：循环里没有 `sleep`，一旦 `is_retriable` 开始返回 `True`，重试之间是零间隔 —— 限流场景下等于没退避。
- **`exceptions` 只增不减**，没有按异常类型去重，长时间重试会攒一长串。
- **`max_retry` 没有配置入口**，调一次就得在代码里写死。
