# Tool Permission Manager

工具级权限控制子插件：按 `config.yaml` 的权限表，在每个请求前把当前身份无权使用的工具从运行时上下文里摘掉。摘掉之后模型看不见这些工具，工具执行器也拿不到它们。

## 权限类型

| `permission` | 含义 |
| --- | --- |
| `admin` | 仅 `miaoli_bot` 根配置 `account.admin_id` 指定的管理员 |
| `white_list` | 该条目 `white_list` 名单里的 QQ 号 |
| `anyone` | 任何调用者 |
| `passerby` | 任何**非管理员**的调用者（即 `admin` 的补集） |
| `nobody` | 谁都不可用（等于把该工具彻底下架，但仍会在权限表里留一行占位） |

## 配置

`config.yaml` 已随根配置一起 `gitignore`（各部署环境取值不同，不入库），从模板复制一份再改：

```bash
cp plugins/tool_permission_manager/config.example.yaml plugins/tool_permission_manager/config.yaml
```

```yaml
enable: true

permissions:
  - tool_name: "bash"
    permission: "admin"
  - tool_name: "read_file"
    permission: "white_list"
    white_list: ["10001", "10002"]
  - tool_name: "list_memes"
    permission: "anyone"
```

未在权限表中声明的工具会被直接摘除并打印一条 warning（默认拒绝），新增工具后记得补配置。

> ✅ **`config.yaml` 缺失时 `enable` / `debug` 都走默认值 `true`**，即「插件照常生效 + 打印 warning」。
> 此时权限表为空，所有工具都会被摘掉（默认拒绝）—— 宁可误杀，也不会漏放重要工具。
> 日志里能看到每个被隐藏的工具名，照它往 `permissions` 里补条目即可。

## 注意事项

- **不做任何过滤的情况**：`enable` 为 `false`、本插件未被加载、或加载过程中抛错时，权限节点不会注册，即全部工具放行。权限的强制力依赖本插件正常运行，不要随意关闭。
- **覆盖范围**：只覆盖「模型经 `call_llm` 请求工具」这条路径；若有节点或子插件直接 `await` 工具的 `ainvoke`，会绕过本插件。
- **日志**：未声明工具的 warning 每次请求都会打印，未做去重，日志中重复出现属于预期行为。
