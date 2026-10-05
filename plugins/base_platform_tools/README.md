本插件提供了 LLM 基础的平台工具：
- `send_message_to_qq`: 给 QQ 好友或群发送消息
- `send_file_to_qq`: 给 QQ 好友或群发送文件
- `download_qq_file`: 下载 QQ 平台发来的文件到本地
- `query_qq_message_id`: 按消息 ID 查询消息详情
- `delete_qq_message`: 撤回指定消息

返回值统一走 `utils.tool_result_builder` 的 `{"status": bool, "message": …}` 契约。
