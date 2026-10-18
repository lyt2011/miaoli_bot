# MCP Adapter Demo

MCP 适配演示子插件：接入 [MCP（Model Context Protocol）](https://modelcontextprotocol.io/) server，
把它暴露的工具**追加**进本项目的工具表，从而让模型能直接调用外部 MCP 工具。

与其它子插件的区别：**本插件不注册任何自己的工具、也不参与事件接收**。
它只做一件事 —— 在图跑到 `on_before_request` 时，把 MCP server 的工具拉一遍，
塞进本次请求的 `runtime.context["tools"]`。

## 工作流程

`recall_mcp_tools` 节点挂在 `on_before_request`，`priority=MEDIUM`（=10）：

- 高于 `base_topology` 默认 `Goto` 的 `MINIMUM`，因此一定会被执行
- 高于 `tool_permission_manager` 的 `pick_tools`（`priority=1`），**这一点是必须的** ——
  `pick_tools` 会把「未配置权限的工具」从 `runtime.context["tools"]` 里摘掉，
  如果 `recall_mcp_tools` 排在它后面，MCP 工具就会被追加回来，**绕过整套权限控制**

也就是说 **MCP 工具默认是被隐藏的**，需要在 `tool_permission_manager` 的 `config.yaml` 里
为每个 MCP 工具显式写一条权限才能被模型看到。这与该插件「未配置即隐藏」的哲学一致。

节点逻辑：

1. 从 `SHARE_STORE` 取本插件的 `PluginConfig`
2. 用 `mcps` 里每个 server 的 `transport.model_dump()` 拼出连接表，构造 `MultiServerMCPClient`
3. `await client.get_tools()` 拿到 MCP 工具（已是 langchain 的 `BaseTool`）
4. 把当前工具表和 MCP 工具**都按 `name` 建成字典**，`raw_tools.update(mcp_tools)` 后写回列表

第 4 步是**按名字去重**，而不是直接 `extend`：

- 同名时 MCP 工具**覆盖**原有条目，不会重复出现
- 不同名的 MCP 工具追加在末尾
- 于是每个请求看到的 MCP 工具都只有一份，**不会随 turn 数无界增长**

> ⚠️ 目前只做到了「去重」，**没做到「下架」**：如果 MCP server 撤掉了某个工具，
> 上一轮注入的旧条目仍会留在工具表里（因为字典里没有「上一轮注入了哪些」这个信息）。
> 代码里已用 `FIXME` 标出。

之所以挂 `on_before_request` 而不是 `on_agent_start`：`runtime.context` 是**每次请求独立**的字典，
每次请求前重新拉一遍工具，服务端工具清单变了能立刻跟上，也不会跨请求累积。

> 注意 `runtime.context["tools"]` 来自 `ToolRegistry.tools` 这个 **property**（每次返回新 list），
> 所以写回只影响本次请求，不会污染全局工具注册表。

## 配置

`config.yaml` 已随根配置一起 `gitignore`（不入库），从模板复制一份再改：

```bash
cp plugins/mcp_adapter/config.example.yaml plugins/mcp_adapter/config.yaml
```

```yaml
enable: true
tool_prefix: true
mcps:
  - name: "omniqq"
    transport:
      transport: "streamable_http"
      url: "http://127.0.0.1:3000/mcp"
      timeout: 30
      headers: {}
  - name: "local_fs"
    transport:
      transport: "stdio"
      command: "python"
      args: ["/opt/mcp/fs_server.py"]
      cwd: "/opt/mcp"
      env: {}
```

| 键 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `enable` | `bool` | `true` | 为 `false` 时只写 `SHARE_STORE`、不挂节点 |
| `tool_prefix` | `bool` | `true` | 传给 `MultiServerMCPClient` 的 `tool_name_prefix`，给 MCP 工具名加上 `<server>_` 前缀 |
| `mcps` | `List[MCPServer]` | `[]` | MCP server 列表，`name` 不能重复（`server_dedup` 校验器） |

`mcps` 为空时插件照常加载，只是不会带来任何工具。

### MCPServer

| 键 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `name` | `str` | 必填 | 服务器名字，也用作工具名前缀与连接字典的键 |
| `reusable` | `bool` | `false` | 是否可复用。**本插件的配置字段，不是 MCP 连接参数** |
| `transport` | `StdioTransport \| StreamableHttpTransport` | 必填 | 传输配置，见下节 |

> **`reusable` 为什么在 `MCPServer` 而不是 `transport` 里**：
> 它回答的是「这个 server 的 tools 列表会不会变」，与传输方式正交 ——
> 稳定工具列表的 stdio server 和 http server 都适合开，动态注册工具的都不适合。
> 传输方式只影响复用的**收益大小**（stdio 省子进程启动 + 握手，http 省一次 `list_tools` 往返），
> 不影响**要不要缓存**。
>
> 参数构造只用到 `name` 和 `transport.model_dump()`，因此 `reusable` 不需要
> `Field(exclude=True)` 也不会污染 MCP 连接字典。

**行为**：`reusable: true` 的 server 在**第一次** `get_tools()` 后从客户端列表移除、
工具进缓存，后续只读缓存；`reusable: false` 的 server 每轮都重新 `list_tools()`。

> 代价：`reusable: true` 的 server 如果中途更新了工具，需要重启 ncatbot 才能看到。

### transport

`transport` 字段是**判别字段**，两种取值对应两种传输。

**`stdio`** —— 拉起一个子进程

| 键 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `command` | `str` | 必填 | 可执行文件 |
| `cwd` | `Optional[str \| Path]` | `None` | 工作目录 |
| `args` | `List[str]` | `[]` | 参数列表 |
| `env` | `Dict[str, str]` | `{}` | 环境变量 |

**`streamable_http`** —— 连一个 HTTP 端点

| 键 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `url` | `str` | 必填 | MCP 端点地址 |
| `timeout` | `Union[float, int]` | `30.0` 秒 | 调用超时。int 会被 `align_timeout_type` 校验器统一转成 `float`（对齐官方声明的 `float \| timedelta`） |
| `headers` | `Dict[str, Any]` | `{}` | 扩展请求头 |

## 依赖

`manifest.toml` 里已声明：

- `langchain-mcp-adapters` —— 提供 `MultiServerMCPClient`（`langchain_mcp_adapters.client`）
- `mcp` —— MCP 协议 SDK，由上面那个包带进来

> `langchain.mcp`（`langchain` 元包里的 beta 命名空间）是**另一套东西**：
> 它导出的是 `MCPAdapter` / `as_langchain_tool`，需要额外的 `fastmcp`，**不提供 `MultiServerMCPClient`**。
> 本插件用的是官方稳定包 `langchain-mcp-adapters`。

## 目录结构

```
mcp_adapter/
├── plugin.toml                     # 入口声明
├── main.py                         # 入口类 MCPAdapter
├── README.md
├── config.example.yaml             # 配置模板（config.yaml 已 gitignore，不入库）
├── __init__.py
├── consts/
│   ├── __init__.py
│   └── share_store_keys.py         # PLUGIN_CONFIG / RAW_CONFIG
├── core/
│   └── mcp_adapter.py              # 占位，尚未使用
├── models/
│   ├── __init__.py
│   ├── plugin_config.py            # PluginConfig（enable / tool_prefix / mcps）
│   ├── mcp_server.py               # MCPServer（name + transport）
│   └── transports/
│       ├── __init__.py
│       ├── base_transport.py       # BaseTransport
│       ├── stdio.py                # StdioTransport
│       └── streamable_http.py      # StreamableHttpTransport
└── nodes/
    ├── __init__.py
    └── recall_mcp_tools.py         # recall_mcp_tools 节点
```

## 已知取舍

- **`reusable: false` 的 server 每次请求都会重新 `list_tools()`。** 对 `streamable_http` 只是一次建连，代价可接受；
  对 `stdio` 则意味着**每个请求都会重新拉起一次子进程**。如果接的是启动开销大的 stdio server，
  把它的 `reusable` 设为 `true` 即可（工具进缓存、客户端从列表移除，不再重建）。
- **工具名冲突**：MCP 工具按 `name` **覆盖**进工具表（`raw_tools.update(mcp_tools)`），同名时 MCP 工具顶掉原有条目、不会重复出现。
  开 `tool_prefix` 可以规避「本地工具被 MCP 工具顶掉」这种意外覆盖。
- 本插件**不参与事件接收**：事件仍由 `ob11_adapter` 经 ncatbot 提供，本插件只扩展**工具**这一侧。
