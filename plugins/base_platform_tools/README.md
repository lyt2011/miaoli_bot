本插件提供了 LLM 基础的平台工具：
- `send_message_to_qq`: 给 QQ 好友或群发送消息
- `send_file_to_qq`: 给 QQ 好友或群发送文件
- `download_qq_file`: 下载 QQ 平台发来的文件到本地
- `query_qq_message_id`: 按消息 ID 查询消息详情
- `delete_qq_message`: 撤回指定消息
- `send_poke`: 戳一戳指定用户（`group_id` 有值为群内戳，无值为私聊戳）

返回值统一走 `utils.tool_result_builder` 的 `{"status": bool, "message": …}` 契约。

## 目录结构

```
base_platform_tools/
├── plugin.toml
├── main.py         # 入口类 BasePlatformTools，on_load 逐个 register_tool
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

工具文件统一从 `miaoli_bot.stores` / `miaoli_bot.consts` / `miaoli_bot.utils` 取共享容器与返回构造器，
平台 API 由 `SHARE_STORE.recall(NCATBOT_API)` 取得。
