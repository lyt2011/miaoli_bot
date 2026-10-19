# Miaoli Bot Adapter

miaoli_bot 内部数据适配 —— 把 miaoli_bot 自己的数据**适配**成图节点可直接消费的形状，供图节点使用。

## 定位：与 `ob11_adapter` 对称

| 插件 | 适配的对象 | 数据来源 |
| --- | --- | --- |
| `ob11_adapter` | **信息**（QQ 事件 / 消息段） | ncatbot |
| `miaoli_bot_adapter` | **miaoli_bot 内部数据**（根配置、供应商、模型等） | miaoli_bot |

`ob11_adapter` 让图节点不必依赖 ncatbot 的类，本插件让图节点不必依赖 miaoli_bot 的根配置结构。

## 节点

| 节点 | 事件 / 优先级 | 产出 |
| --- | --- | --- |
| `inject_model_info` | `on_turn_start`（`NORMAL + 1`） | `base_url` / `api_key` / `model` / `max_tokens` 四个 state 键，供 `build_client` 构造 [OI] 实例 |
| `inject_soul` | `on_turn_start`（`NORMAL + 1`） | `prompt` 的 `soul` 段，内容是根配置 `prompt_file` 指向的人设全文 |

两个节点都必须排在 `build_client`（`NORMAL`）之前 —— `inject_model_info` 是它的输入，`inject_soul` 则是为了让 `prompt_builder` 在 `on_before_request` 拼装时能读到人设。

## 目录结构

```
miaoli_bot_adapter/
├── plugin.toml                 # 插件声明（入口文件 / 入口类）
├── main.py                     # 入口类 MiaoliBotAdapter
├── config.example.yaml         # 配置模板（config.yaml 已 gitignore，不入库）
├── consts/                     # SHARE_STORE 键（PLUGIN_CONFIG / RAW_CONFIG）
├── models/                     # PluginConfig
└── nodes/                      # inject_model_info / inject_soul
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
