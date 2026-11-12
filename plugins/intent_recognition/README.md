用配置里的规则匹配本轮最后一条消息，命中就把对应工作流文件的内容拼成一条 `HumanMessage` 追加进 `messages`。

`recognize_intent` 挂在 `on_turn_start`（`NORMAL`）。它**只往 `messages` 里加一条消息**，不碰 `state["prompts"]`，所以系统提示词的内容和长度每轮完全一致 —— 前缀缓存不会因为意图命中而失效。

## 目录结构

```
intent_recognition/
├── metadata.toml                # 元信息（name / entry_class / description / dependences）
├── __init__.py
├── main.py                      # IntentRecognition，读配置 + 注册节点
├── config.example.yaml          # 配置模板
├── consts/
│   ├── __init__.py
│   └── share_store_keys.py      # PLUGIN_CONFIG / RAW_CONFIG 的 store 键
├── protocols/
│   ├── __init__.py
│   ├── rule.py                  # BaseRule：is_hit 的抽象方法
│   └── workflow.py              # BaseWorkflow：content 的抽象属性
├── models/
│   ├── __init__.py
│   ├── plugin_config.py         # PluginConfig：enable + workflows
│   ├── workflows/
│   │   ├── __init__.py
│   │   └── file_workflow.py     # FileWorkflow + 判别式联合 Workflow
│   └── rules/
│       ├── __init__.py
│       ├── any_keywords.py      # AnyKeywordsRule
│       ├── min_keywords.py      # MinKeywordsRule
│       ├── regex.py             # RegexRule
│       └── single_keyword.py    # SingleKeywordRule
├── nodes/
│   ├── __init__.py
│   └── recognize_intent.py      # 节点本体
└── utils/
    ├── __init__.py
    └── sugar.py                 # build_prompt 拼标签串 / content_to_text 提取正文
```

## 配置

```yaml
enable: false

workflows:
  - mode: "file"                # 判别字段，必须显式写
    name: "meme"
    file: "/abs/path/to/meme.md"
    encoding: "utf-8"
    rules:
      - mode: "single_keyword"
        word: "表情包"
```

| 键 | 说明 |
| --- | --- |
| `enable` | 关闭时 `on_load` 直接返回，节点不注册 |
| `workflows` | 工作流列表，可空 |
| `workflows[].mode` | 判别字段，**必须显式写**，目前只有 `"file"` |
| `workflows[].name` | 标签名，注入后形如 `<meme>…</meme>` |
| `workflows[].file` | 工作流文件，**绝对路径**，必须真实存在 |
| `workflows[].encoding` | 读 `file` 用的编码，默认 `utf-8` |
| `workflows[].rules` | 命中判据，至少 1 条 |

`file` 是 `FilePath`，路径不存在会在加载期抛 `ValidationError`。`mode` 和每条 rule 的 `mode` 都是判别字段，**省略不会被默认值兜底**，即使模型里写了 `default`。

## 匹配流程

### 1. 取待匹配文本

只看 `messages` 的**最后一条**，且它必须是 `HumanMessage` 或 `AIMessage`：

```python
messages = state.get("messages", [])
if not messages:
	return None

if not isinstance(messages[-1], (AIMessage, HumanMessage)):
	return None

content = content_to_text(messages[-1])
```

末条是 `ToolMessage`（工具刚跑完）或其它类型时直接返回 `None`，不注入。

取正文交给 `content_to_text`，是为了**多模态消息**：直接 `str(content)` 会拿到 Python 的 repr，把 `image_url`、`base64` 这些元数据一起带进待匹配文本，关键词和正则就会在元数据上误命中。

`content` 是列表时逐块交给 `block_to_text`，只有两种块会被收下：**带 `str` 型 `text` 键的字典块**、以及**裸字符串块**；其余（图片块、`tool_use` 块等）一律跳过，返回空串。

| 输入 | 结果 |
| --- | --- |
| `[{"type":"text","text":"这图好看"}, {"type":"image_url",...}]` | `'这图好看'` |
| `["裸字符串", {"type":"text","text":"dict块"}]` | `'裸字符串\ndict块'` |
| `[{"type":"image_url",...}]` | `''` |
| `[{"type":"tool_use",...}]` | `''` |

### 2. 逐 workflow 判定

一个 workflow 下的多条 rule 是**「与」关系** —— `all()`，全部命中才算这个 workflow 命中：

```python
hited = all([rule.is_hit(content) for rule in workflow.rules])
```

注意这是个容易读反的地方：rule 之间不是「任意一条命中」，而是「一条不满足就整体不命中」。想表达「任意一条」，就把多个关键词写进同一个 `any_keywords` rule 的 `words` 里。

workflow 之间则是各自独立判定，多个 workflow 可以同时命中。

### 3. 读取工作流正文

命中后取 `content` 属性，它会按 `encoding` 读 `file`：

```python
segments[workflow.name] = workflow.content
```

`content` 是 `BaseWorkflow` 上的抽象属性，`FileWorkflow` 的实现就是读文件。想加别的来源（内联字符串、HTTP），实现同一个属性即可，节点不用动。

变量名 `segments` 记的是「**标签 → 正文**」这层映射，累积完整个交给 `build_prompt`。

### 4. 拼装与注入

`build_prompt` 把字典拼成 `<name>内容</name>`，用换行连接（`cr` 默认 `"\n"`）：

```python
cr.join([f"<{o_o}>{T_T}</{o_o}>" for o_o, T_T in dt.items()])
```

**所有命中项合成一条消息**，外面再套一层固定标签 `TAG`，前面加一行固定引导语 `GUIDE`：

```python
text = build_prompt(segments)
text = GUIDE + "\n" + text
text = f"<{TAG}>\n" + text + f"\n</{TAG}>"

return {"messages": [HumanMessage(text)]}
```

`GUIDE` 是 `"以下本轮的意图识别注入内容。"`，`TAG` 是 `"intent-recognition"`。

两个 workflow 都命中时，追加进 `messages` 的那条消息长这样：

```
<intent-recognition>
以下本轮的意图识别注入内容。
<meme>…</meme>
<privacy>…</privacy>
</intent-recognition>
```

`workflow.name` 是内层子标签，`intent-recognition` 是外层标签。外层标签和原来的 `prompts["intent-recognition"]` 段名一致，语义没有漂移。

## 两个抽象

| 协议 | 抽象成员 | 实现方 |
| --- | --- | --- |
| `BaseRule` | `is_hit(data) -> bool` | 四种 rule |
| `BaseWorkflow` | `content` (property) -> `str` | `FileWorkflow` |

`models/` 下的两个 `__init__.py` 各自导出一个判别式联合，形态一致：

```python
Rule = Annotated[Union[AnyKeywordsRule, MinKeywordsRule, RegexRule, SingleKeywordRule],
                 Field(discriminator="mode")]

Workflow = Annotated[Union[FileWorkflow], Field(discriminator="mode")]
```

新增一种 rule = 在 `models/rules/` 下加一个类、继承 `BaseRule` 实现 `is_hit`、写一个 `Literal` 的 `mode`、加进该文件 `Union`。

新增一种 workflow 来源 = 在 `models/workflows/` 下加一个类、继承 `BaseWorkflow` 实现 `content`、写一个 `Literal` 的 `mode`、加进该文件 `Union`。

两种情况节点都不用动。

## 四种 rule

| mode | 字段 | 判定 |
| --- | --- | --- |
| `single_keyword` | `word` | `word in data` |
| `any_keywords` | `words` | 任意一个命中 |
| `min_keywords` | `words`、`count`（默认 1） | 命中数量 `>= count` |
| `regex` | `regex` | `re.search`，命中子串即可 |

三个关键字 rule 的名字说的是**命中数量**，不是「命中方式」：`single_keyword` 收单个 `word`、命中即真；`any_keywords` 收 `words`、任意一个命中就算；`min_keywords` 也收 `words`，但要**至少命中 `count` 个**才算。

注意 `count` 默认 1 时「至少 1 个」与「任意一个」等价，所以 `min_keywords` 不写 `count` 也能当「或」用 —— 想表达「或」就老老实实写 `any_keywords`，别依赖这个巧合。

`RegexRule` 在首次调用时编译正则并缓存到 `PrivateAttr`，之后复用同一个 `Pattern`。

## 容错

节点本体**没有** `try / except`。判定和读取都在循环里直接进行，配置在加载期已经校验过（`file` 必须真实存在），所以正常运行期不会有预期内的异常。

例外是文件在加载后被删或编码不对 —— 这会直接抛出去。要加兜底就在读取处包一层。

## 优先级

```python
registry.on(ON_TURN_START, recognize_intent, priority=NORMAL)
```

`register()` 内部是 `reverse=True` 排序，**priority 数值越大越先执行**；但 priority 只在**同一个图节点内**给处理器排序，跨节点先后由图里的边决定。

`prompt_builder` 挂在 `ON_BEFORE_REQUEST`（`NORMAL`），和本节点不是同一个事件，两边的 priority 没有可比性。注入能赶在拼装之前靠的是流程顺序：`ON_TURN_START` 之后直接到 `ON_BEFORE_REQUEST`（`default_routing` 的 `on_turn_start` → `ON_BEFORE_REQUEST`），`build_prompt` 是那个事件里的处理器。`build_prompt` 会用 `Overwrite([SystemMessage, *messages])` 整个替换 `messages`，先注入的消息因此会进到重建后的列表里。

`main.py` 里那行注释原本写的是「必须早于 `prompt_builder` 的 `NORMAL + 1`（数值大者先跑），否则拼装时读不到本轮增删的段」—— 跨事件比 priority 和「增删段」都是改写前的说法，现已改为「与 `prompt_builder` 不在同一个事件上，跨事件比 priority 没有意义；先后由 `default_routing` 的跳转决定」。

## 没命中时

`segments` 为空时直接返回 `None`，什么都不注入：

```python
if not segments:
	return None
```

这一步是必需的。`messages` 走 `add_messages`，追加进历史的 `HumanMessage` **会永久留在对话里**（还有 checkpoint）。如果未命中时也照样注入，每一轮都会留下一条只剩标签和引导语的空壳，越攒越多。改版前这段落在 `prompts` 里，节点每轮都会把同名段整个覆写一遍，所以不需要这个判断 —— 换成 `messages` 之后就必须有。
