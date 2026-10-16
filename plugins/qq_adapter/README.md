QQ 平台适配 —— 把 ncatbot 的 QQ 事件**解析**成平台无关的字典，供图消费。

## 定位：纯 adapter

**只解析，不发送、不回复。** 回复由 core 的 `main.py` 负责（读图的 `final_answer`，切块 + 打字延迟后发回 QQ）。
发送能力在 `qq_platform_tools` 子插件里。所以本插件只依赖 ncatbot 的**数据形状**，不依赖它的实现。

## 目录结构

```
qq_adapter/
├── plugin.toml
├── main.py             # 入口类 QQAdapterPlugin，on_load 显式逐个注册
├── config.example.yaml  # 配置模板（config.yaml 已 gitignore，不入库）
├── api/                # Registry：本插件自己的解析器注册器（register_segment_parser / register_event_parser）
├── chains/             # 解析链：ChainProtocol / BaseParserChain / EventParseChain / SegmentParseChain
├── consts/             # SHARE_STORE 键（PLUGIN_CONFIG / RAW_CONFIG / EVENT_PARSER / SEGMENT_PARSER / REGISTRY）
├── models/             # DispatchResult / PluginConfig / SplitConfig
├── nodes/              # handle_event
├── parsers/            # 两级解析器
│   ├── parser.py       #   Parser 协议（@runtime_checkable，鸭子类型）
│   ├── event_parsers/  #   群 / 私聊事件解析器
│   └── segment_parsers/#   文本 / AT / 图片 / 文件 / 引用消息段解析器
└── utils/              # parse_segments
```

## `handle_event` 节点

挂在 `on_agent_start`（`priority=HIGH`），从 `state["event"]`（core 传进来的 `event._data.model_dump()`）出发：

1. 交给 `EventParseChain` 解析 → `event_data` 字典
2. 把 `event_data` 回填进 `state["event"]`（供 `tool_permission_manager` 读 `sender.user_id`）
3. 把 `event_data` 序列化成 JSON 塞进 `HumanMessage`，追加进 `messages`

## 解析链与解耦

解析器是 `@runtime_checkable` 的 `Parser` 协议（`is_accept` / `handle`），**完全吃字典**，不 import ncatbot 的任何类：

- 事件解析器用 `data["message_type"]` 判别：`"group"` / `"private"`
- 段解析器用 `data["type"]` 判别：`"text"` / `"at"` / `"reply"` / `"file"` / `"image"`

`is_accept` 是「类型 + 形状」双判：判别位用 `.get()`（缺了也不抛），字段用 `isinstance` 校验；
所以畸形 / 无关 dict 一律返回 `False`，不会把解析链炸掉。

## 字典形状（`event._data.model_dump()`）

```
message_type : "private" | "group"
post_type / sub_type / message_id / user_id / raw_message / font / platform / self_id / time
sender       : { ... }
message      : [ {"type": …, "data": {…}}, … ]      # 段数组
# 群消息额外: group_id / group_name / anonymous
```

段（`seg.to_dict()`）：

| 段 | `type` | `data` 字段 |
| --- | --- | --- |
| `At` | `"at"` | `qq`（注意不是 `user_id`）|
| `PlainText` | `"text"` | `text` |
| `Reply` | `"reply"` | `id` |
| `File` | `"file"` | `file` / `url` / `file_id` / `file_size` / `file_name` |
| `QQImage` | `"image"` | 同上 + `sub_type` |
