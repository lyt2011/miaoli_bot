QQ 平台工具 —— 把消息 / 文件发回 QQ，以及查询、撤回。

| 工具 | 作用 |
| --- | --- |
| `send_message_to_qq` | 给 QQ 好友或群发送消息 |
| `send_file_to_qq` | 给 QQ 好友或群发送文件 |
| `download_qq_file` | 下载 QQ 平台发来的文件到本地 |
| `query_qq_message_id` | 按消息 ID 查询消息详情 |
| `delete_qq_message` | 撤回指定消息 |
| `send_poke` | 戳一戳指定用户（`group_id` 有值为群内戳、无值为私聊戳） |

## 目录结构

```
qq_platform_tools/
├── metadata.toml
├── main.py         # 入口类 QQPlatformTools，on_load 逐个 register_tool
├── README.md
└── tools/          # 全部工具（一个工具一个文件）
    ├── __init__.py
    ├── send_message.py
    ├── send_file.py
    ├── download_file.py
    ├── query_message_id.py
    ├── delete_message.py
    └── send_poke.py
```

工具文件统一从 `miaoli_bot.stores` / `miaoli_bot.consts` / `miaoli_bot.utils` 取共享容器与发送封装
（`easier_send`），平台 API 由 `SHARE_STORE.recall(NCATBOT_API)` 取得。返回值统一是
`{"status": bool, ...}` 字典，失败时带 `message`。

本插件**不读任何配置**（`self.config` 恒为 `{}`），因此没有 `config.yaml`。

## 与 `ob11_adapter` 的分工

- `ob11_adapter` 管**进**：把 ncatbot 事件解析成图能吃的字典。
- 本插件管**出**：把消息 / 文件发回 QQ。

两者都只依赖 core，互不依赖。
