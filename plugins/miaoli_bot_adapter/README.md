# Miaoli Bot Adapter

miaoli_bot 内部数据适配 —— `on_load` 把根配置解析成 `PluginConfig` 放进 `SHARE_STORE`（子插件经 `miaoli_bot.api.get_root_config()` 取），省得每个节点自己解析 `providers` 列表。LLM 客户端**不再经由本插件**：那件事由 `base_llm.api.build_client()` + `base_nodes` 的 `build_client` 节点负责。

此外，**人格这份提示词资产也归本插件持有**（`data/SOUL.md`），主包不再内置任何提示词、也不再提供 `prompt_file` / `get_prompt`。提示词只有人设这一份：怎么输出、说多长不写进提示词，交给模型自己判断。

## 定位：与平级插件 `miaoli_qq_channel` 对称

| 插件 | 负责的输入 | 产出 |
| --- | --- | --- |
| `miaoli_qq_channel`（**平级插件**，与本包同级目录，不是本包的子插件） | **信息**：QQ 事件 / 消息段（ncatbot 的 `MessageEvent`） | **结构化输入**：它自带的 `QQChannel`（`name = "qq"`，经 `miaoli_bot.api.register_channel()` 进 `ChannelRegistry`），`drain()` 给出 `BaseChannelMessage`，`to_text()` 交出这一回合的文本、`thread_id` 说明它属于哪个会话 |
| `miaoli_bot_adapter`（本插件） | **miaoli_bot 内部数据**：根配置 + 人格资产（`SOUL.md`）+ 图的进出口（`input` / `output`） | 根配置 → `SHARE_STORE`；人格资产 → `prompts` 的 `soul` 段；`input` → 一条 `HumanMessage`，末条消息 → `output` |

`miaoli_qq_channel` 让图节点不必依赖 ncatbot 的事件类（它的消息段模型在 `plugins/qq_platform_tools/models/messages/`，入库结构是 `core/channel/qq_channel_message.py`），本插件让图节点不必依赖 miaoli_bot 的根配置结构。

## 节点

| 节点 | 事件 / 优先级 | 产出 |
| --- | --- | --- |
| `input_to_messages` | `on_agent_start`（`MEDIUM`） | 把 `state["input"]` 包成一条 `HumanMessage` 追加进 `messages` |
| `inject_soul` | `on_turn_start`（`MEDIUM`） | `prompts` 的 `soul` 段，内容是 `data/SOUL.md` 全文 |
| `messages_to_output` | `on_agent_end`（`TRIVIAL`） | 把 `messages[-1].content` 写进 `state["output"]` |

`inject_soul` 挂 `on_turn_start`，比 `prompt_builder` 的 `on_before_request` 早一个事件，所以它写的段一定赶在拼装之前就位。

`input_to_messages` / `messages_to_output` 是图的**进出口**：调用方只往 `state["input"]` 里放 `to_content()` 的原样返回，不再自己拼 `HumanMessage`；出图时同理，`main.py` 只读 `state["output"]`，不再从 `messages` 末条里猜回复。两个字段都是 `UntrackedValue` 通道，**不落 checkpoint**，所以每轮调用方必须重新给 `input`。

`messages_to_output` 注册在 `TRIVIAL`（`-1000`）：要排在 `base_nodes` 的 `output_checker`（`LOWEST`，`-100`）之后借它确认末条是 `AIMessage`，又要排在 `default_routing` 的 `on_agent_end`（`MINIMUM`，`-9999`）之前 —— 那个节点返回 `Goto(END)`，同优先级下会短路后面所有处理器。末条不是 `AIMessage`、或带 `tool_calls` / `invalid_tool_calls` 时它返回 `Abort` 而不是写值。

## 人格资产

| 文件 | 段名 | 内容 |
| --- | --- | --- |
| `data/SOUL.md` | `soul` | 她是谁：身份 / 称呼 / 脾气 / 口吻 / 颜文字 / 自我认知 |

**每轮读盘**，改完 `md` 文件不用改代码，下一轮就生效。路径由 `WORKSPACE` 这个 store 键拿到的插件目录拼出（`workspace / "data" / "SOUL.md"`），所以部署时只换文件、不换配置。

提示词里只有这一份。输出格式、长度、分条这些约束不写成资产 —— 它们跟着渠道走，写进提示词就是把提示词和渠道绑死。

## 目录结构

```
miaoli_bot_adapter/
├── metadata.toml               # 元信息（name / entry_class / description / dependences）
├── main.py                     # 入口类 MiaoliBotAdapter
├── config.example.yaml         # 配置模板（config.yaml 已 gitignore，不入库）
├── README.md                   # 本文件
├── consts/                     # SHARE_STORE 键（PLUGIN_CONFIG / RAW_CONFIG / WORKSPACE）
├── data/                       # 人格资产（SOUL.md）
├── models/                     # PluginConfig
└── nodes/                      # input_to_messages / inject_soul / messages_to_output
```

## 配置

`config.yaml` 已随根配置一起 `gitignore`（各部署环境取值不同，不入库），从模板复制一份再改：

```bash
cp plugins/miaoli_bot_adapter/config.example.yaml plugins/miaoli_bot_adapter/config.yaml
```

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enable` | `bool` | `true` | 是否启用该插件 |

## 容器键

| 常量 | 值 | 内容 |
| --- | --- | --- |
| `PLUGIN_CONFIG` | `miaoli_bot/subplugin/miaoli_bot_adapter.models.plugin_config` | 校验后的 `PluginConfig` |
| `RAW_CONFIG` | `miaoli_bot/subplugin/miaoli_bot_adapter.plugin_config` | 原始 `config.yaml` 字典 |
| `WORKSPACE` | `miaoli_bot/subplugin/miaoli_bot_adapter.workspace` | 本插件的目录（`Path`），`on_load` 时写入，供 `inject_soul` 拼 `data/SOUL.md` 的路径 |
