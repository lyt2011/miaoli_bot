用配置里的规则匹配最后一轮消息，命中就把对应提示词文件的内容拼成一段注入 `state["prompt"]`。

`recognize_intent` 挂在 `on_before_request`，比 `prompt_builder` 早一步执行 —— 它只负责产出 `intent_recognition` 这一段，拼成 `SystemMessage` 落到 `messages[0]` 是 `prompt_builder` 的事。

## 目录结构

```
intent_recognition/
├── plugin.toml               # 入口声明（enter_file / enter_class）
├── __init__.py
├── main.py                   # IntentRecognition，读配置 + 注册节点
├── config.example.yaml       # 配置模板
├── consts/
│   ├── __init__.py
│   └── share_store_keys.py   # PLUGIN_CONFIG / RAW_CONFIG 的 store 键
├── protocols/
│   ├── __init__.py
│   └── rule.py               # BaseRule：is_hit 的抽象方法
├── models/
│   ├── __init__.py
│   ├── plugin_config.py      # PluginConfig：enable + matchers
│   ├── match_.py             # Match + 判别式联合 Rule
│   └── rules/
│       ├── __init__.py
│       ├── any_keywords.py   # AnyKeywordsRule
│       ├── min_keywords.py   # MinKeywordsRule
│       ├── regex.py          # RegexRule
│       └── single_keyword.py # SingleKeywordRule
├── nodes/
│   ├── __init__.py
│   └── recognize_intent.py   # 节点本体
└── utils/
    ├── __init__.py
    └── helper.py             # build_prompt 拼标签串 / get_content 提取正文
```

## 配置

```yaml
enable: false

matchers:
  - name: "meme"
    file: "/abs/path/to/meme.md"
    encoding: "utf-8"
    rules:
      - mode: "single_keyword"
        word: "表情包"
```

| 键 | 说明 |
| --- | --- |
| `enable` | 关闭时 `on_load` 直接返回，节点不注册 |
| `matchers` | 匹配器列表，可空 |
| `matchers[].name` | 标签名，注入后形如 `<meme>…</meme>` |
| `matchers[].file` | 要注入的提示词文件，**绝对路径**，必须真实存在 |
| `matchers[].encoding` | 读 `file` 用的编码，默认 `utf-8` |
| `matchers[].rules` | 命中判据，至少 1 条 |

`file` 是 `FilePath`，路径不存在会在加载期抛 `ValidationError`；全字段 `extra="forbid"`，键名拼错也直接报错；每条 rule 的 `mode` 必须显式写 —— 它是判别字段，省略不会被默认值兜底。

## 匹配流程

### 1. 取待匹配文本

不管最后一条消息是什么类型，都交给 `get_content` 提取正文：

```python
latest_content = get_content(messages[-1])
```

`get_content` 的参数类型是 `Any` —— 它只鸭子类型地读 `content`，不依赖具体消息类（也就不必为了一个类型注解去 import 消息类）：

```python
if not (content := getattr(ctx, "content", None)):
    return None

if isinstance(content, list):
    blocks: List[str] = []
    for b in content:
        match b:
            case {"text": str(b_text)}: blocks.append(b_text)
            case str(): blocks.append(b)
            case _: ...
    text = cr.join(blocks)
else:
    text = str(content)
```

绕这一层是为了**多模态消息**：直接 `str(content)` 会拿到 Python 的 repr，把 `image_url`、`base64` 这些元数据一起带进待匹配文本，关键词和正则就会在元数据上误命中。

列表里的块只有两种会被收下：**带 `str` 型 `text` 键的字典块**、以及**裸字符串块**；其余（图片块、`tool_use` 块等）一律跳过。

| 输入 | 结果 |
| --- | --- |
| `[{"type":"text","text":"这图好看"}, {"type":"image_url",...}]` | `'这图好看'` |
| `["裸字符串", {"type":"text","text":"dict块"}]` | `'裸字符串\ndict块'` |
| `[{"type":"image_url",...}]` | `''` |
| `[{"type":"tool_use",...}]` | `''` |

返回 `None` 的情况：末条消息没有 `content`、或者 `content` 本身是假值（`""` / `[]`）。

### 2. 逐 matcher 判定

一个 matcher 下的多条 rule 是**「与」关系** —— `all()`，全部命中才算这个 matcher 命中：

```python
if all([rule.is_hit(latest_content) for rule in matcher.rules]):
```

注意这是个容易读反的地方：rule 之间不是「任意一条命中」，而是「一条不满足就整体不命中」。想表达「任意一条」，就把多个关键词写进同一个 `keywords` rule 的 `words` 里。

matcher 之间则是各自独立判定，多个 matcher 可以同时命中。

### 3. 读取提示词

命中后按 `encoding` 读 `file`，键取 `name`：

```python
field_prompts[matcher.name] = Path(matcher.file).read_text(encoding=matcher.encoding)
```

变量名 `field_prompts` 记的是「**字段 → 提示词**」这层映射：键是注入后要用的标签名，值是该标签对应的提示词正文。它累积完整个交给 `build_prompt`，本身不表示「命中了什么」。

### 4. 拼装与注入

`build_prompt` 把字典拼成 `<name>内容</name>`，用换行连接（`cr` 默认 `"\n"`）：

```python
cr.join([f"<{o_o}>{T_T}</{o_o}>" for o_o, T_T in dt.items()])
```

**所有命中项合成一个段**，段名固定为 `intent_recognition`：

```python
return {"prompt": {"intent_recognition": build_prompt(field_prompts)}}
```

所以提示词里长这样（两个 matcher 都命中时）：

```
<intent_recognition><meme>…</meme>
<privacy>…</privacy></intent_recognition>
```

`matcher.name` 是段内的子标签，不是段名。

## 四种 rule

| mode | 字段 | 判定 |
| --- | --- | --- |
| `single_keyword` | `word` | `word in data` |
| `any_keywords` | `words` | 任意一个命中 |
| `min_keywords` | `words`、`count`（默认 1） | 命中数量 `>= count` |
| `regex` | `regex` | `re.search`，命中子串即可 |

三个关键字 rule 的名字说的是**命中数量**，不是「命中方式」：`single_keyword` 收单个 `word`、命中即真；`any_keywords` 收 `words`、任意一个命中就算；`min_keywords` 也收 `words`，但要**至少命中 `count` 个**才算。

注意 `count` 默认 1 时「至少 1 个」与「任意一个」等价，所以 `min_keywords` 不写 `count` 也能当「或」用 —— 想表达「或」就老老实实写 `any_keywords`，别依赖这个巧合。

四种都实现 `BaseRule.is_hit(data) -> bool`，`mode` 是判别字段。新增一种命中方式 = 在 `models/rules/` 下加一个类、实现 `is_hit`、写一个 `Literal` 的 `mode`、加进 `models/match_.py` 的 `Union`，节点不用动。

`RegexRule` 在首次调用时编译正则并缓存到 `PrivateAttr`，之后复用同一个 `Pattern`。

## 容错

每个 matcher 的处理都包在 `try / except` 里：

```python
try:
    if all([...]):
        field_prompts[matcher.name] = Path(matcher.file).read_text(...)
except Exception as e:
    LOGGER.error(f"匹配 {matcher.name} 时出现错误: {type(e).__name__}: {e}")
```

文件在加载后被删、编码不对、正则写错，都只让**这一个 matcher 失效**，不影响其它 matcher，也不会让节点抛异常。失败会以 `ERROR` 级别打出 matcher 名和异常类型，日志里能查到。

## 优先级

```python
self.registry.on_before_request(recognize_intent, priority=NORMAL + 2)
```

`register()` 内部是 `reverse=True` 排序，**priority 数值越大越先执行**。`prompt_builder` 的 `build_prompt` 挂的是 `NORMAL + 1`，本节点必须严格**大于**它，否则段写进去时 prompt 已经拼完了。

## 没命中时

`field_prompts` 为空时 `build_prompt({})` 返回空串，节点仍然返回：

```python
{"prompt": {"intent_recognition": ""}}
```

也就是该段被置为空字符串而不是删除，`prompt_builder` 会渲染出一个空的 `<intent_recognition></intent_recognition>`。这样做的好处是上一轮命中的内容不会残留 —— 每轮都覆盖，不留陈旧段。
