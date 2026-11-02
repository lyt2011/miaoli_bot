# Miaoli Bot Adapter

miaoli_bot 内部数据适配 —— `on_load` 把根配置解析成 `PluginConfig` 放进 `SHARE_STORE`（子插件经 `miaoli_bot.api.get_root_config()` 取），省得每个节点自己解析 `providers` 列表。LLM 客户端**不再经由本插件**：那件事由 `miaoli_bot.api.build_client()` + `base_nodes` 的 `build_client` 节点负责。

此外，**人格与输出协议这两份提示词资产也归本插件持有**（`data/`），主包不再内置任何提示词、也不再提供 `prompt_file` / `get_prompt`。

## 定位：与 `ob11_adapter` 对称

| 插件 | 适配的对象 | 数据来源 |
| --- | --- | --- |
| `ob11_adapter` | **信息**（QQ 事件 / 消息段） | ncatbot |
| `miaoli_bot_adapter` | **miaoli_bot 内部数据**（根配置 → `SHARE_STORE`）+ **人格资产**（`SOUL.md` / `output_protocol.md`） | miaoli_bot / 本插件 `data/` |

`ob11_adapter` 让图节点不必依赖 ncatbot 的类，本插件让图节点不必依赖 miaoli_bot 的根配置结构。

## 节点

| 节点 | 事件 / 优先级 | 产出 |
| --- | --- | --- |
| `inject_soul` | `on_turn_start`（`NORMAL + 1`） | `prompts` 的 `soul` 段，内容是 `data/SOUL.md` 全文 |
| `inject_output_protocol` | `on_turn_start`（`NORMAL + 1`） | `prompts` 的 `output_protocol` 段，内容是 `data/output_protocol.md` 全文 |

两个节点都挂 `on_turn_start`，比 `prompt_builder` 的 `on_before_request` 早一个事件，所以它们写的段一定赶在拼装之前就位。

## 人格资产

| 文件 | 段名 | 内容 |
| --- | --- | --- |
| `data/SOUL.md` | `soul` | 她是谁：身份 / 外貌 / 脾气 / 口吻 |
| `data/output_protocol.md` | `output_protocol` | 怎么输出：长度 / 接话 / 松弛 / 符号 / 分寸 / 消息边界 / 回复通道 / 标点 / 语序 / 输出格式 |

两份都是**每轮读盘**的，改完 `md` 文件不用改代码，下一轮就生效。路径由 `WORKSPACE` 这个 store 键拿到的插件目录拼出（`workspace / "data" / "SOUL.md"`），所以部署时只换文件、不换配置。

拆分的判据：**去掉聊天场景还成立的写进 `soul`，必须看对方怎么发才决定怎么回的写进 `output_protocol`。**

## 目录结构

```
miaoli_bot_adapter/
├── metadata.toml               # 元信息（name / entry_class / description / dependences）
├── main.py                     # 入口类 MiaoliBotAdapter
├── config.example.yaml         # 配置模板（config.yaml 已 gitignore，不入库）
├── README.md                   # 本文件
├── consts/                     # SHARE_STORE 键（PLUGIN_CONFIG / RAW_CONFIG / WORKSPACE）
├── data/                       # 人格资产（SOUL.md / output_protocol.md）
├── models/                     # PluginConfig
└── nodes/                      # inject_soul / inject_output_protocol
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
| `WORKSPACE` | `miaoli_bot/subplugin/miaoli_bot_adapter.workspace` | 本插件的目录（`Path`），`on_load` 时写入，供两个提示词节点拼 `data/` 下的路径 |
