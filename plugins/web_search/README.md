# Web Search

联网搜索子插件：注册一个 `web_search` 工具给模型，把搜索结果原文交给它自己读。

`adapter` 选后端，但**只影响工具的入参 schema 和返回数据形状，不影响工具名** —— 不管选哪个后端，模型看到的工具都叫 `web_search`。

## 工作方式

`on_load` 里做三件事：

1. 校验配置，把 `PluginConfig` / 原始配置 / `aiohttp.ClientSession` 写进 `SHARE_STORE`
2. `enable: false` 时到此为止，**不注册工具**
3. 否则按 `TOOL_MAPPING[config.adapter]` 注册**一个**工具

同一时刻只有一个后端生效，两个工具对象都叫 `web_search`，靠 `TOOL_MAPPING` 二选一：

```python
TOOL_MAPPING = {
	"langsearch": lang_search,
	"deepseek": deepseek_search,
}
```

## 配置

```yaml
enable: true
adapter: "deepseek"
api_url: "https://api.deepseek.com/v1/tools/search"
api_key: "sk-..."
```

- `enable`：`false` 时只写 `SHARE_STORE`、不注册工具。
- `adapter`：后端名，`langsearch` / `deepseek` 二选一。
- `api_url`：请求地址，**填完整路径**。这一点和根配置的 `providers.base_url` 不同 —— 后者由 SDK 自己拼 `/chat/completions`，只填到 `/v1`；这里是插件自己 `post`，填什么就请求什么。
- `api_key`：搜索服务的密钥，**必填**。

`config.yaml` 已随根配置一起 `gitignore`（各部署环境取值不同，不入库），模板见 `config.example.yaml`。

## 两个后端

### `langsearch`

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `query` | **必填** | 搜索关键词 |
| `count` | `5` | 返回条数，`1 ~ 50` |
| `freshness` | `noLimit` | 时间范围：`noLimit` / `oneDay` / `oneWeek` / `oneMonth` / `oneYear` |
| `include_domains` | `[]` | 只在这些域名里搜 |
| `exclude_domains` | `[]` | 排除这些域名 |
| `timeout` | `30.0` | 请求超时（秒） |

请求体里域过滤字段必须用 **camelCase**（`includeDomains` / `excludeDomains`）—— 服务端只认这个，传 snake_case 不报错、HTTP 200、**静默忽略**。

请求体固定带 `"summary": False` 关掉 `summary` 字段（该后端的 `summary` 与 `snippet` 逐字重复，关掉省约 68% 体积；此为旧版实测结论，本次未复测）。

### `deepseek`

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `query` | **必填** | 搜索内容，不能全空，`1 ~ 128` 字符 |
| `count` | `10` | 返回条数，`1 ~ 50` |
| `ori_question` | `null` | 用户的原始问题，帮助引擎理解意图；可省略，传了就不能全空 |
| `timeout` | `10.0` | 请求超时（秒） |

请求体固定带 `"need_content": False` —— 必须关，否则响应会再叠一层正文把上下文炸掉。

`query` 支持 `site:` / `-site:` 与引号等搜索语法。

## 返回值

成功：`{"results": <服务端原始响应 JSON>}`

失败：`{"message": "联网搜索出错: <异常类型>: <详情>"}`

**除入参校验外不会抛异常** —— 响应码非 200、超时、连接失败全部走 `message` 分支，模型能读到错误原因。实测：

| 场景 | 返回 |
| --- | --- |
| 错误路径（404） | `{"message": "联网搜索出错: RuntimeError: 服务器响应码: 404"}` |
| 超时（`timeout=0.001`） | `{"message": "联网搜索出错: TimeoutError: "}` |
| `query` 全空 | 抛 `ValidationError`（工具入参 schema 拦住） |
| `count=51` | 抛 `ValidationError` |

### 响应结构（`deepseek` 实测）

外层 `{"results": {"results": [...]}}`，单条字段：

| 字段 | 说明 |
| --- | --- |
| `title` | 标题 |
| `url` | 链接 |
| `summary` | 正文抽取，**体积占 80%** |
| `snippet` | 短摘要（单条实测 354 字符） |
| `content` | 恒为空串（`need_content: False` 关掉了） |
| `site_name` / `site_icon` / `date` / `authority` / `rerank_score` | 元数据 |

与 `langsearch` 不同，`deepseek` 的 `summary` 与 `snippet` **不是同一份内容**（实测 3551 字符 vs 354 字符）。

本插件**不做字段过滤，原始响应整体交给模型** —— 过滤省不了多少，却要维护一套解析逻辑。

## 英文优先

**实测英文检索质量明显优于中文**（`langsearch`，同一后端、同一时间、仅换语言；数据来自 v0.14.0，本次未复测）：技术 / 包名类 query 英文相关率约 **65%**、中文约 **30%**。

| Query | 结果 |
| --- | --- |
| `What is NcatBot` | 命中 PyPI 的 `ncatbot 4.4.1.post1`、`ncatbot5 5.5.7` ✅ |
| `NcatBot 是什么` | 全变成 Netcat 音近词（0/5）❌ |
| `What is LangGraph checkpoint` | 3/5 命中 PyPI 的 `langgraph-checkpoint` 系列 ✅ |
| `LangGraph checkpoint 是什么` | 1/5 ❌ |
| `latest news today` | 4/5 命中 thelocal / standard.co.uk 等 ✅ |
| `今天有什么新闻` | 0/5 ❌ |

`lang_search` 的 docstring 里已注明「任何时候都优先使用英文」，模型会自己翻译后再搜。

## Token 开销

单次搜索体积主要由 `count` 决定（`deepseek` 实测，`need_content: False`）：

| `count` | 字符数 | 约 token（字符 / 3.5） |
| --- | --- | --- |
| 1 | 4,828 | ~1,379 |
| 3 | 13,941 | ~3,983 |
| **5** | **21,887** | **~6,253** |
| 10 | 43,780 | ~12,508 |

体积的 **80% 是 `summary`**（整页正文抽取，单条最长见过 3,500+ 字符）。`count` 填 50 时按线性外推约 6 万 token，一次就能吃掉 128K 窗口的一半 —— 默认值是刻意保守的。

## 加新后端

1. `models/plugin_config.py` 的 `Adapter` 里加名字
2. `tools/` 下新建工具文件，装饰器统一用 `@tool("web_search", args_schema=...)`
3. `tools/__init__.py` 导出
4. `main.py` 的 `TOOL_MAPPING` 加一行

工具名保持 `web_search` 不变 —— 换后端对模型应当是透明的，只换 schema 和数据源。

## 依赖与生命周期

`aiohttp`（`>=3.13.4`）。`ClientSession` 在 `on_load` 建、`on_close` 关：先 `drop` 掉 `SHARE_STORE` 里的三个键再 `await close()`，避免中途报错导致键残留。

`SHARE_STORE` 键（`consts/share_store_keys.py`）：

| 键 | 值 |
| --- | --- |
| `PLUGIN_CONFIG` | 校验后的 `PluginConfig` |
| `RAW_CONFIG` | 原始配置字典 |
| `CLIENT_SESSION` | 共享的 `aiohttp.ClientSession` |

工具通过 `miaoli_bot.api.store_recall` 取配置，**不直接碰 `SHARE_STORE`**。
