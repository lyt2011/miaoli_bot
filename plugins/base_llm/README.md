# Base LLM

模型接入层 —— **库里没有节点**，不注册任何事件，提供两个能力：`build_client`（把根配置变成一个 `BaseChatModel` 实例）与 `call_llm`（带重试地发一次请求）。

## 为什么单独成插件

「模型」这件事原来被摊在主包里：`api/llm_ops.py` 同时管着根配置的 `llm` 段解析（`build_client` / `get_model_info`）和三个 langchain 供应商实现的选择表（`CLIENT_MAPPING`），而调用点各自 `await client.ainvoke(messages)` —— 一旦要加退避、按异常类型分流、统计失败次数，每个调用点都得抄一遍。

于是把「配置 → 客户端」的翻译（`build_client` / `CLIENT_MAPPING` / `get_client_cls`）和「客户端 → 回复」的调用（`call_llm`）都收进这里：主包不再 import 任何 `langchain_openai` / `langchain_deepseek` / `langchain_anthropic`，对「有哪些供应商实现」彻底无感，只保留根配置的 schema（`PluginConfig.llm` 必须在启动时校验）。

**配置 schema 不在这里**，它属于主包的根配置模型：子插件反向给主包提供类型会破坏单向依赖，也会让 `config.yaml` 的 `llm` 段从「启动即校验」退化成「插件加载时才校验」。

## 目录

| 路径 | 内容 |
|---|---|
| `api/` | 对外门面：只转出两个能力 `build_client` / `call_llm`。常量、工具函数与异常类不在这里中转，要用就 `from base_llm.consts` / `base_llm.utils` / `base_llm.errors` |
| `core/` | `build_client`（配置 → 客户端）+ `call_llm`（重试循环本体） |
| `consts/` | `CLIENT_MAPPING`：`openai` / `deepseek` / `anthropic` 对应的 langchain 实现 |
| `utils/` | `get_client_cls`（查实现类）+ `is_retriable`（异常可重试判据，**目前恒 `False`**） |
| `errors/` | 尝试次数耗尽时抛的异常，继承主包的 `BaseBotError` |

## 对外契约

`api/` 只放「做什么」：`build_client` 与 `call_llm`。异常类、常量表、工具函数各有自己的层，直接从那层 import —— 不经过 `api` 中转，免得多一条要同步的出口。

```python
def build_client(provider_name: str, model_name: str) -> BaseChatModel
```

从根配置（`miaoli_bot.api.get_root_config()`）里按名字找 provider 与 model，再按 `provider.client` 选实现类。找不到分别抛主包的 `ProviderNotFound` / `ModelNotFound` / `ClientNotFound`。名字必须显式传 —— 不再像以前那样不传就取 `config.llm.provider`，这样调用方可以给压缩、给判定单独指定便宜的模型。

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

## 现状：`call_llm` 零调用点

`build_client` 已接线：`base_nodes/nodes/build_client.py` 在 `ON_TURN_START` 里用它建客户端（`metadata.toml` 里 `base_nodes` 声明了对本插件的依赖）。

但 `call_llm` 还没接：`base_nodes/nodes/call_llm.py`（节点）与 `base_compact/core/compact_now.py` 目前都还是直接 `await client.ainvoke(...)`。

节点那个 `call_llm` 与本插件的 `call_llm` **是两个不同的东西**：节点签名是 `(state, runtime)`，本插件是 `(messages, client, *, max_retry)`。搬过来只是把能力放到了能独立演进的位置，接线还没做。

## 已知短板

- **`is_retriable` 恒 `False`**，重试机制整个是空转的（见上）。
- **没有退避**：循环里没有 `sleep`，一旦 `is_retriable` 开始返回 `True`，重试之间是零间隔 —— 限流场景下等于没退避。
- **`exceptions` 只增不减**，没有按异常类型去重，长时间重试会攒一长串。
- **`max_retry` 没有配置入口**，调一次就得在代码里写死。
