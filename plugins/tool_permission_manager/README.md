# Tool Permission Manager

工具授权子插件：按 `config.yaml` 的授权表，在每个请求前把**未放行**的工具从运行时上下文（`runtime.context["tool_surface"]`）里摘掉。摘掉之后模型看不见这些工具，工具执行器也拿不到它们。

## 判定规则

每条权限由工具名和 `allowed` 组成，`allowed` 有三种取值：

| `allowed` | 效果 |
| --- | --- |
| `"all"` | 所有会话都保留该工具 |
| `["private-xxx", "group-yyy", ...]` | 只有列表里的 `thread_id` 保留该工具 |
| `null` / `[]` / 不写 | 一律摘除 |
| 未在授权表中声明 | **一律摘除**（默认拒绝），`debug` 为 `true` 时打一条 warning |

判定用的是 `get_config()["configurable"]["thread_id"]`，也就是这一轮消息所属的会话，形如 `private-3757973483`、`group-1046279455`。会话标识由通道侧生成，同一个 QQ 号在私聊和群聊里是两个不同的 `thread_id`。

判定在 `ON_BEFORE_REQUEST` 阶段完成，优先级 `LOW`(-10)；`is_allowed` 在 `utils/is_allowed.py` 里。

> 早期版本按调用者身份（`admin` / `white_list` / `anyone` / `passerby` / `nobody`）区分权限，
> 入口改成通道之后改成了全局 `allow` / `refuse` 二值表，再改回按 `thread_id` 授权 ——
> 现在粒度是「会话」，不是「人」：能拿到某个私聊 `thread_id` 就等于拿到那个人对应的授权。

## 配置

`config.yaml` 已随根配置一起 `gitignore`（各部署环境取值不同，不入库），从模板复制一份再改：

```bash
cp plugins/tool_permission_manager/config.example.yaml plugins/tool_permission_manager/config.yaml
```

```yaml
enable: true
debug: true                      # 对未配置的工具打 warning

permissions:

  # 只给某个人用
  - name: "bash"
    allowed: ["private-3757973483"]

  # 所有会话都能用
  - name: "web_search"
    allowed: "all"

  # 谁都不能用（等同于不写这条，但留在表里有据可查）
  - name: "write"
    allowed: null
```

新增工具后记得补条目，否则它会被默认摘除。

> ✅ **`config.yaml` 缺失时 `enable` / `debug` 都走默认值 `true`**，即「插件照常生效 + 打印 warning」。
> 此时授权表为空，所有工具都会被摘掉（默认拒绝）—— 宁可误杀，也不会漏放重要工具。
> 日志里能看到每个被隐藏的工具名，照它往 `permissions` 里补条目即可。

## 文件结构

```
tool_permission_manager/
├── consts/          # 共享存储键
├── models/          # Permission（含 Allowed 别名）/ PluginConfig
├── nodes/           # pick_tools：ON_BEFORE_REQUEST 上的判定节点
├── utils/           # is_allowed：单条授权的判定函数
└── config.example.yaml
```

## 注意事项

- **用旧配置会静默失效**：`allowed` 是唯一生效的字段，老版本写的 `mode` 会被 pydantic 当作多余字段忽略，`allowed` 落到默认 `[]` —— 结果不是报错，而是**所有工具被摘光**。升级时先改配置再重启。
- **不需要显式写拒绝**：不写条目、写 `null`、写 `[]` 效果相同，区别只是留在表里有据可查。
- **不做任何过滤的情况**：`enable` 为 `false`、本插件未被加载、或加载过程中抛错时，权限节点不会注册，即全部工具放行。权限的强制力依赖本插件正常运行，不要随意关闭。
- **覆盖范围**：只覆盖「模型经 `call_llm` 请求工具」这条路径；若有节点或子插件直接 `await` 工具的 `ainvoke`，会绕过本插件。
- **日志**：未声明工具的 warning 每次请求都会打印，未做去重，日志中重复出现属于预期行为。
