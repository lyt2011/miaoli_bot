# Web Search

联网搜索子插件：给模型一个 `lang_search` 工具，把搜索结果原文交给它自己读。

**设计上支持多后端** —— `config.yaml` 的 `provider` 选后端，`on_load` 按它决定注册哪个工具。目前只适配了 `langsearch`，其余后端（`tavily` / `brave` / `serper` 等）留了位置但没写：`Provider` 是个 `Literal["langsearch"]`，要加后端就往里加名字、再在 `main.py` 的 `if` 链里补一条、`tools/` 下加一个对应工具。

## 配置

```yaml
enable: true
provider: "langsearch"
base_url: "https://api.langsearch.com/v1/web-search"
env_key: "SEARCH_API_KEY"
```

- `enable`：为 `false` 时只写 `SHARE_STORE`、不注册工具。
- `provider`：后端名。决定注册哪个工具。
- `base_url`：请求地址，**填完整路径**（不像根配置的 `providers` 那样只填到 `/v1`）。
- `env_key`：**密钥从哪个环境变量读**。默认 `SEARCH_API_KEY`。

## 密钥

**密钥不写在 `config.yaml` 里。** 子插件的 `config.yaml` 随仓库提交（`.gitignore` 有 `!plugins/*/config.yaml` 例外），写进去就会泄露，所以走环境变量：

```bash
export SEARCH_API_KEY="sk-..."
```

`PluginConfig` 用 `PrivateAttr` 存 `_api_key`，由 `model_validator(mode="after")` 从 `os.environ[self.env_key]` 读入，对外只暴露只读属性 `api_key` —— 因此密钥也不会出现在 `repr` / `model_dump` 里。

环境变量没设时 `api_key` 是**空串**（不抛异常），请求会被服务端以 `401 Invalid API KEY` 拒绝，工具返回 `fail`。systemd 部署记得加 `Environment=` 或 `EnvironmentFile=`。

## 工具 `lang_search`

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `query` | **必填** | 搜索词 |
| `count` | `5` | 返回条数，`1 ~ 50` |
| `freshness` | `noLimit` | 时间范围，可选 `noLimit` / `oneDay` / `oneWeek` / `oneMonth` / `oneYear` |
| `include_domains` | `[]` | 只在这些域名里搜 |
| `exclude_domains` | `[]` | 排除这些域名 |
| `timeout` | `30.0` | 请求超时（秒） |

请求体里域过滤字段名必须用 **camelCase**（`includeDomains` / `excludeDomains`）—— 服务端只认这个，传 snake_case 不报错、HTTP 200、**静默忽略**。

返回值是 `success(响应 JSON)`（原文整体交给模型）或 `fail("联网搜索出错: ...")`。

## 用英文搜

**实测英文检索质量明显优于中文**（同一后端、同一时间，仅换语言）：技术 / 包名类 query 英文相关率约 **65%**、中文约 **30%**，差距最大。

| Query | 结果 |
| --- | --- |
| `What is NcatBot` | 命中 PyPI 的 `ncatbot 4.4.1.post1`、`ncatbot5 5.5.7` ✅ |
| `NcatBot 是什么` | 全变成 Netcat 音近词（0/5）❌ |
| `What is LangGraph checkpoint` | 3/5 命中 PyPI 的 `langgraph-checkpoint` 系列 ✅ |
| `LangGraph checkpoint 是什么` | 1/5 ❌ |
| `latest news today` | 4/5 命中 thelocal / standard.co.uk 等 ✅ |
| `今天有什么新闻` | 0/5 ❌ |

工具 docstring 里已注明「任何时候都优先使用英文」，模型会自己翻译后再搜。

## Token 开销

单次搜索的体积主要由 `count` 决定（`summary: false` 下实测）：

| `count` | token |
| --- | --- |
| 1 | 679 |
| **5（默认）** | **1929** |
| 10 | 5099 |
| 20 | 10390 |
| 50（上限） | 27786 |

模型自己把 `count` 填成 50 就是一次吃掉 2.8 万 token，默认 5 是刻意的保守值。

响应里的 `summary` 字段与 `snippet` **逐字完全相同**（同一份正文抽取的两个字段名），请求时传 `summary: false` 关掉，省 **68%**。返回的 `displayUrl` 与 `url` 也是重复的。

响应信封噪声（`log_id` / `_type` / `queryContext` / `usage` 等）只占约 **14%**，而 `snippet` 是整页正文抽取（平均 856 字/条，实测最长 5256 字）—— 所以本插件**不做字段过滤，原始响应整体交给模型**：过滤最多省 14%，却要维护一套解析逻辑。

## 依赖

`aiohttp`（`>=3.13.4`）。`ClientSession` 在 `on_load` 建、`on_close` 关（先 `drop` 掉 `SHARE_STORE` 里的键再 `await close()`，避免残留引用）。
