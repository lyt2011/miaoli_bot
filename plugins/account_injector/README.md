把账号信息注入系统提示词。

`inject_account` 节点挂在 `on_agent_start`，把管理员 / 机器人的 QQ 号与昵称拼成一个信息块，加上根配置里的人设，一起写进 `system_prompt`。

`system_prompt` 是普通键（没有 reducer），每轮直接覆盖，不会越积越多。
