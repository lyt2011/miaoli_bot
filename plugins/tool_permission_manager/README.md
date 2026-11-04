# Tool Permission Manager

工具级权限控制子插件：按 `config.yaml` 的权限表，在每个请求前把**未放行**的工具从运行时上下文（`runtime.context["tool_surface"]`）里摘掉。摘掉之后模型看不见这些工具，工具执行器也拿不到它们。

## 判定规则

每条权限只有一个二值开关：

| `mode` | 效果 |
| --- | --- |
| `allow` | 保留该工具 |
| `refuse` | 摘除该工具 |
| 未在权限表中声明 | **一律摘除**（默认拒绝），`debug` 为 `true` 时打一条 warning |

判定在 `ON_BEFORE_REQUEST` 阶段完成，优先级 `1`。

> 早期版本按调用者身份（`admin` / `white_list` / `anyone` / `passerby` / `nobody`）区分权限。
> 入口改成通道之后，一张图同时服务多个通道、多个会话，节点拿不到「这一轮是谁在说话」，
> 所以改成全局的 `allow` / `refuse` 二值表 —— **身份不再参与判定**。

## 配置

`config.yaml` 已随根配置一起 `gitignore`（各部署环境取值不同，不入库），从模板复制一份再改：

```bash
cp plugins/tool_permission_manager/config.example.yaml plugins/tool_permission_manager/config.yaml
```

```yaml
enable: true
debug: true                      # 对未配置的工具打 warning

permissions:
  - name: "web_search"
    mode: "allow"
  - name: "send_message_to_qq"
    mode: "allow"
  - name: "bash"
    mode: "refuse"
```

新增工具后记得补条目，否则它会被默认摘除。

> ✅ **`config.yaml` 缺失时 `enable` / `debug` 都走默认值 `true`**，即「插件照常生效 + 打印 warning」。
> 此时权限表为空，所有工具都会被摘掉（默认拒绝）—— 宁可误杀，也不会漏放重要工具。
> 日志里能看到每个被隐藏的工具名，照它往 `permissions` 里补条目即可。

## 注意事项

- **不需要显式写 `refuse`**：不写条目和写 `refuse` 效果相同，区别只是后者留在表里有据可查。
- **不做任何过滤的情况**：`enable` 为 `false`、本插件未被加载、或加载过程中抛错时，权限节点不会注册，即全部工具放行。权限的强制力依赖本插件正常运行，不要随意关闭。
- **覆盖范围**：只覆盖「模型经 `call_llm` 请求工具」这条路径；若有节点或子插件直接 `await` 工具的 `ainvoke`，会绕过本插件。
- **日志**：未声明工具的 warning 每次请求都会打印，未做去重，日志中重复出现属于预期行为。