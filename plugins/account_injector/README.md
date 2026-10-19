把账号信息注入提示词。

`inject_account` 节点挂在 `on_agent_start`，把管理员 / 机器人的 QQ 号与昵称拼成一个信息块，写进 `prompt` 的 `account_info` 段。

## 为什么是「段」而不是整串

`prompt` 的类型是 `Dict[str, str]`，通道是 `miaoli_pipeline` 的 `SectionPatch` —— 按 key 打补丁。本插件只负责**产出自己那段**，人设、风格、工具说明等其它段由别的子插件各自写，互不覆盖。

拼装成一条 `SystemMessage` 并放到 `messages[0]` 是 `prompt_builder` 子插件的职责。

写入 `None` 表示删除该段：

```python
return {"prompt": {"account_info": None}}
```
