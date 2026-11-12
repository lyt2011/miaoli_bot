# MCP Adapter

MCP 适配子插件：接入 [MCP（Model Context Protocol）](https://modelcontextprotocol.io/) server，
把它暴露的工具**追加**进本轮请求的工具表，从而让模型能直接调用外部 MCP 工具。

与其它子插件的区别：**本插件不注册任何自己的工具、也不参与事件接收**。
它只做一件事 —— 在图跑到 `on_agent_start` 时，把 MCP server 的工具拉一遍，
塞进本轮的 `runtime.context["tool_surface"]`。

## 工作流程

`inject_mcp_tools` 节点挂在 `on_agent_start`，`priority=MEDIUM`（=10）。

### 为什么是 `on_agent_start`

| 事件 | 本插件 | `tool_permission_manager` |
|---|---|---|
| `on_agent_start` | ✅ `inject_mcp_tools`（`MEDIUM` = 10） | — |
| `on_before_request` | — | ✅ `pick_tools`（`priority=LOW`） |

`GRAPH_EVENTS` 里 `on_agent_start` 排在 `on_before_request` 之前，所以顺序天然是：

```
inject_mcp_tools   →  把 MCP 工具加进工具表
pick_tools         →  把没配 allow 的工具摘掉（包括刚加进来的 MCP 工具）
```

**这个顺序是必须的**：`pick_tools` 的语义是「未配置即摘除」，如果 `inject_mcp_tools` 排在它后面，
MCP 工具会被追加回来，**绕过整套权限控制**。

也就是说 **MCP 工具默认是不可见的**，需要在 `tool_permission_manager` 的 `config.yaml` 里
为每个 MCP 工具名显式写一条 `mode: "allow"` 才能被模型看到。

### 节点逻辑

1. 从 `SHARE_STORE` 取本插件的 `MCPClientRegistry`
2. `await client_registry.get_tools()` 拿到 MCP 工具（已是 langchain 的 `BaseTool`）
3. 逐个 `tool_surface.add(tool)`

`ToolSurface.add` 是**按 `name` 幂等覆盖**的：

- 同名时 MCP 工具**顶替**原有条目，不会重复出现（同时打一条 warning）
- 不同名的 MCP 工具追加进表
- 于是一次请求里每个工具名只有一份

### 不做「下架」也没关系

工具的落点是 `runtime.context["tool_surface"]`，而这个 surface 是**每轮新建**的
（跑图入口每轮从 `ToolRegistry.to_surface()` 生成一份副本）。
所以 MCP server 撤掉某个工具后，下一轮的表里自然就没有了 —— 不存在「旧条目残留」。
同理，写进去的工具也不会污染全局 `ToolRegistry`。

### 节点返回 `None`

`inject_mcp_tools` 不往 `GraphState` 写任何东西，它改的是 `runtime.context` 里的对象。
返回 `None` 在管线里被识别为「无操作」，不会产生 state 更新 —— 但 `tool_surface` 已经被就地改过了。

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
├── metadata.toml                   # 元信息（name / entry_class / description / dependences）
├── main.py                         # 入口类 MCPAdapter
├── README.md
├── config.example.yaml             # 配置模板（config.yaml 已 gitignore，不入库）
├── __init__.py
├── consts/
│   ├── __init__.py
│   └── share_store_keys.py         # PLUGIN_CONFIG / RAW_CONFIG / MCP_CLIENT_REGISTRY
├── core/
│   ├── __init__.py
│   └── mcp_client_registry.py      # MCPClientRegistry（注册 / 复用缓存 / get_tools）
├── models/
│   ├── __init__.py
│   ├── plugin_config.py            # PluginConfig（enable / tool_prefix / mcps）
│   ├── mcp_server.py               # MCPServer（name / reusable / transport）
│   ├── runtimes/
│   │   ├── __init__.py
│   │   └── mcp_client.py           # MCPClient（reusable + client）
│   └── transports/
│       ├── __init__.py
│       ├── base_transport.py       # BaseTransport
│       ├── stdio.py                # StdioTransport
│       └── streamable_http.py      # StreamableHttpTransport
├── protocols/
│   ├── __init__.py
│   └── tool_obtainable.py          # ToolObtainanle（async get_tools）
└── nodes/
    ├── __init__.py
    └── inject_mcp_tools.py         # inject_mcp_tools 节点
```

## 已知取舍

- **`reusable: false` 的 server 每次请求都会重新 `list_tools()`。** 对 `streamable_http` 只是一次建连，代价可接受；
  对 `stdio` 则意味着**每个请求都会重新拉起一次子进程**。如果接的是启动开销大的 stdio server，
  把它的 `reusable` 设为 `true` 即可（工具进缓存、客户端从列表移除，不再重建）。
- **工具名冲突**：`ToolSurface.add` 按 `name` 覆盖，同名时 MCP 工具顶掉原有条目并打 warning。
  开 `tool_prefix` 可以规避「本地工具被 MCP 工具顶掉」这种意外覆盖。
- **权限默认关闭**：MCP 工具名是动态的，`tool_permission_manager` 的权限表里没有它们，
  所以默认全部被摘除。要么给每个工具名写 `mode: "allow"`，要么接受「MCP 工具只能手工放行」这件事。
- 本插件**不参与事件接收**：QQ 事件由**平级插件** `miaoli_qq_channel`（与本包同级目录，不是本包的子插件）记录，再由它自带的 `QQChannel` 经 `miaoli_bot.api.register_channel()` 注册成消息通道交给主包；本插件只扩展**工具**这一侧。