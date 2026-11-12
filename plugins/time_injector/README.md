# Time Injector

按会话间隔把「当前时间」注入对话，同时把一段「`time-inject` 标签怎么读」的说明写进系统提示词。

时间本身是**会变的内容**，说明是**静态内容**，两者走不同的通道 —— 这是本插件唯一的设计要点，见下。

## 两个节点

| 节点 | 事件 | 优先级 | 写哪儿 |
|---|---|---|---|
| `helper_inject` | `ON_AGENT_START` | `NORMAL` | `prompts` 的 `time-inject-helper` 段 |
| `time_inject` | `ON_BEFORE_REQUEST` | `MEDIUM` | `messages` 末尾一条 `HumanMessage` |

## 为什么分成两个通道

`prompts` 的每一段最终都会被 `prompt_builder` 拼进 `messages[0]` 的 `SystemMessage`，也就是**整段输入的头部**。供应商的上下文缓存按前缀匹配，头部一变，后面几万个 token 全部作废、全量计费。

所以：

- **时间值**每秒都在变，绝不能进 `prompts` —— 每轮都会撞碎前缀缓存。它走 `messages` 尾部追加，前缀不动，只有新增的那 78 个字符是未命中的。
- **说明文本**是常量，进 `prompts` 后 `SystemMessage` 每轮逐字符相同，缓存照常命中，边际成本接近 0。

同理，`time_inject` 的优先级 `MEDIUM`(10) 是刻意的：`prompt_builder` 的 `build_prompt` 是 `NORMAL`(0)，本插件要排在它之前，时间块才会落在本轮系统提示词之后、而不是被后续的 `Overwrite` 顺序绕过去。`helper_inject` 挂在 `ON_AGENT_START` 上，每轮跑图只执行一次，而 `ON_TURN_START` 会随工具循环反复进入。

## 注入内容

时间块由 `TAG` 包一层：

```
<time-inject>

Current Time: 2026-11-10 19:41 +0800
Weekday: 2

</time-inject>
```

- 时间格式 `%Y-%m-%d %H:%M %z`，**带时区偏移**（`+0800`）。不带的话模型无法判断 `19:41` 是哪个时区的 19:41。
- **不含秒**：间隔是分钟甚至小时量级（服务器当前 3600 秒），秒位是假精度 —— 一个可能是一小时前的 `19:41:07` 反而更容易被模型当成「刚刚」。
- `Weekday` 取值 `1`–`7`，`1` = 星期一（`datetime.weekday() + 1`）。
- 内置模板是 `consts/prompt.py` 的 `DEFAULT_TEMPLATE`，`template` 配了文件就用文件内容，占位符是 `$now` 与 `$weekday`（`string.Template` 语法）。

说明段（`consts/prompt.py` 的 `HELPER_TEXT`）：

```
<time-inject-helper>
time-inject 注入时刻快照，不会刷新，以最后一条为准
</time-inject-helper>
```

它存在的理由是：`messages` 里的时间块是**注入那一刻**的快照，会一直留在历史里。会话越长，历史里堆的时间块越多，模型可能把最早那条当成"现在"。说明段让模型知道这些块是快照、要以最后一条为准。

## 间隔语义

`LAST_INJECTED_AT` 是 `Dict[thread_id, datetime]`，`on_load` 时初始化为 `{}`，**只存在内存里，重启即清空**。

- 每个会话独立计时：某会话在上一次注入后不满 `interval` 秒就跳过，其它会话不受影响。
- 首轮必注入（没有记录时 `last_at` 为空，直接放行）。
- 时间戳在**构建提示词之前**就写回 `mapping`，所以构建失败（比如模板占位符对不上）时该会话仍会被跳过 `interval` 秒 —— 失败也算「注入过」。

## 配置

`config.example.yaml` 必须复制成 `config.yaml` 才能加载：`on_load` 无条件执行 `PluginConfig.model_validate(self.config)`，缺 `config.yaml` 时 `self.config` 是 `None`，会 `ValidationError` 后被判加载失败。

| 字段 | 默认 | 说明 |
|---|---|---|
| `enable` | `true` | 关闭时既不写共享容器也不注册任何节点 |
| `interval` | `60.0` | 两次注入之间的最小间隔，单位秒，**必须 ≥ 60**（`ge=60`，否则 `on_load` 直接 `ValidationError`）|
| `template` | `null` | 外部模板文件路径，留空用内置模板；文件不存在时**静默回落到内置模板** |
| `encoding` | `utf-8` | 读取模板文件时的编码 |

`template` 只做类型校验（`Optional[Path]`），**不校验文件是否存在** —— 路径写错不会报错，`time_inject` 里 `path.is_file()` 为假就静默用内置模板。要确认外部模板真的生效，得比对注入内容和你文件里的文本。

## 已知短板

- **时间块会在历史里累积**：每次注入都是一条独立 `HumanMessage`，永久留在 checkpoint 里。`interval: 60` 下一个活跃会话每小时最多堆 60 条、约 4,680 字符，且旧块的时间戳与新块互相矛盾（说明段只能缓解，不能消除）。调大 `interval` 是最直接的抑制手段。
- **精度上界就是 `interval`**：间隔期内的请求拿到的是旧快照，"现在几点"最坏会差 `interval` 秒。
- **每会话计时、非全局**：多个群同时活跃时，注入总量是各会话之和，没有全局节流。
