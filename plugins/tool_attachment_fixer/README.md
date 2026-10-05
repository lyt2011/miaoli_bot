修复工具结果里的附件 —— 某些模型不接受 `tool` 消息携带多模态块，直接请求会 `400`。

`fix_tool_attachment` 节点挂在 `on_tool_calling`（`priority=NORMAL-2`），把带附件的 `ToolMessage` 改成纯文本（正文换成 `replace_text`），再把原来的多模态块原样挪进紧跟其后的一条 `HumanMessage`（`id=f"image-{tool_call_id}"`），返回 `Overwrite` 整表替换。文本内容不丢，只是换了个角色承载。

只对 `models` 里声明的模型生效；没有改动时（`is_changed == False`）直接返回 `None` —— 这条守卫是必需的，否则每轮都会把整张消息表写进 `checkpoint_writes`。

## 配置

```yaml
enable: true
models:
  - "deepseek/deepseek-flash"
  - "deepseek-flash"
replace_text: "该工具产生的附件已被添加进入上下文中。"
```

- `models`：生效的模型名单，两种写法都认 —— `<provider>/<model>`（如 `deepseek/deepseek-flash`）与 `<model>`（如 `deepseek-flash`），命中任一即生效。**留空 = 对所有模型生效**。
- `replace_text`：替换后 `ToolMessage` 的正文。

## 与 `base_nodes` 的关系

本节点是从 `base_nodes` 的 `attach_image` 移植过来的，区别只在「模型门控」与「`id` 稳定性」两点 —— `attach_image` 无条件生效，且新建的 `HumanMessage` 不带 `id`。移植后 `base_nodes/nodes/_attach_image.py` 已删除，两处不要同时启用，否则后跑的那个会扫不到附件（前一个已把 `ToolMessage.content` 换成字符串）。
