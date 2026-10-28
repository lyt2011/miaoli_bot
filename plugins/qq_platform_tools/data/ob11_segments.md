# OB11 发送侧消息段速查（NapCat 实现）

发送一条消息 = 按顺序给一个消息段数组，每个元素形如 `{"type": <段类型>, "data": {...}}`。

```json
[
  {"type": "reply", "data": {"id": "746312745"}},
  {"type": "at",    "data": {"qq": "123456789"}},
  {"type": "text",  "data": {"text": " 看一下这个"}},
  {"type": "image", "data": {"file": "/sdcard/a.png"}}
]
```

**段顺序 = 显示顺序**，数组里怎么写就怎么排，没有任何内置顺序。想要「@ 在前、文字在后」就把 `at` 排在 `text` 前面。

---

## 0. 三条铁律

1. **`type` 必须在白名单里**，写错类型名 / 写协议里不存在的段（如 `share`）→ 整条请求抛 `未知的消息类型：xxx`，一条都发不出去。
2. **`data` 里字段名是 NapCat 定的**，不是直觉命名（见 §5 字段名陷阱）。
3. **段级失败是静默的**：某一段的参数不对 → 这一段被丢掉，其它段照发，不报错。只有整条消息一段都没生成出来时，才会抛 `消息体无法解析, 请检查是否发送了不支持的消息类型`。

---

## 1. 可用段

### 1.1 文本类

| type | 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `text` | `text` | str | ✅ | 纯文本，唯一无副作用的段 |
| `face` | `id` | str | ✅ | 系统表情 QSid，如 `"14"`（不是 emoji 字符） |
| | `resultId` | str | | 表情结果 ID，一般不用填 |
| | `chainCount` | int | | 一般不用填 |
| `mface` | `emoji_package_id` | int | ✅ | 商城表情包 ID |
| | `emoji_id` | str | ✅ | 表情 ID |
| | `key` | str | ✅ | 表情 key |
| | `summary` | str | ✅ | 显示用摘要，如 `"[表情]"` |

> `mface` 四个字段**全部必填**，少一个就会被丢弃。这四个值只能从收到的 `mface` 段里原样抄，无法自己编。

### 1.2 媒体文件类（`image` / `record` / `video` / `file`）

这四个段共用同一套字段，区别只在渲染方式：

| type | 说明 |
|---|---|
| `image` | 图片 |
| `record` | 语音（见 §4 第 7 条，依赖 FFmpeg 适配器） |
| `video` | 视频 |
| `file` | 文件（群文件 / 私聊文件） |

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | str | ✅ | **必填字段**。本地绝对路径、http(s) URL 或 `file:///` 都行 |
| `url` | str | | 运行时会**覆盖** `file`（取值优先级 `url` > `file` > `path`） |
| `path` | str | | 本地路径，优先级最低 |
| `name` | str | | 显示的文件名（`file` 段建议填） |
| `thumb` | str | | 封面图（`video` 常用） |
| `summary` | str | | 显示摘要（仅 `image` 有此字段） |
| `sub_type` | int | | 图片子类型，一般不用填（仅 `image` 有此字段） |

> 三个路径字段里 **`file` 是协议必填项**，`url` / `path` 只是可选的覆盖/补充。
> 所以**统一写 `file` 最稳**：本地文件填绝对路径，网络图直接填 URL。
> 真的想覆盖时再单独给 `url`。

### 1.3 卡片类

| type | 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `json` | `data` | str 或 obj | ✅ | 卡片 JSON（字符串或对象都行） |
| | `config` | obj | | `{"token": str}`，token 必填 |
| `markdown` | `content` | str | ✅ | markdown 文本，**需要签名服务** |
| `contact` | `type` | str | ✅ | `"qq"` 或 `"group"` |
| | `id` | str | ✅ | 对应 QQ 号 / 群号 |
| `forward` | `id` | str | ✅ | **已存在**的合并转发 `res_id`，用于转发别人的转发 |
| | `content` | 段数组 | | 可选，`OB11Message[]` |

> 想把「多段消息」打包成一条合并转发，用 `node` 段（§2.3），不是 `forward`。

### 1.4 音乐类（两个互斥变体）

| 变体 | 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| 平台音乐 | `type` | str | ✅ | `"qq"` / `"163"` / `"kugou"` / `"migu"` / `"kuwo"` |
| | `id` | str 或 int | ✅ | 平台歌曲 ID |
| 自定义音乐 | `type` | str | ✅ | 必须是 `"custom"` |
| | `url` | str | ✅ | 点击跳转地址 |
| | `image` | str | ✅ | 封面图 |
| | `audio` | str | | 音频地址 |
| | `title` | str | | 标题 |
| | `content` | str | | 副标题 / 描述 |

> **互斥**：`type="custom"` 时**不能**给 `id`；`type` 是平台名时**不能**给 `url`/`image`。
> 平台音乐依赖签名服务，失败时段被丢弃。

### 1.5 互动类

| type | 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `dice` | `result` | int 或 str | ✅ | 占位值，实际点数由服务端随机 |
| `rps` | `result` | int 或 str | ✅ | 同上，石头剪刀布 |

### 1.6 位置

| type | 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `location` | `lat` | num | ✅ | 纬度 |
| | `lon` | num | ✅ | 经度 |
| | `title` | str | | 标题 |
| | `content` | str | | 描述 |

> 半成品：位置卡片的文本被硬编码成 `"测试"`，扩展字段为空串。能用但不实用。

---

## 2. 有条件才生效的段

### 2.1 `at` —— 只能群聊

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `qq` | str | ✅ | 被 @ 的 QQ 号；@全体成员写 `"all"` |
| `name` | str | | 显示名，可省 |

- **群聊**：正常生效。
- **私聊**：这个段被**静默丢弃**（不报错）。如果整条消息只有 `at` 一段，则会抛 `消息体无法解析`。

### 2.2 `reply` —— 必须有真实消息可引用

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | str | 二选一 | 消息短 ID |
| `seq` | int | 二选一 | 消息序号（**优先于 `id`**） |

- 两个都不给 → 段被丢弃。
- `id` 查不到对应消息 → 只记一条 warning，段被丢弃，消息照发（只是没有引用框）。
- 群聊、私聊都支持。

### 2.3 `node` —— 合并转发节点，独占整条消息

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `nickname` | str | ✅ | 该节点显示的发送者昵称 |
| `content` | 段数组 / str / 单段对象 | ✅ | 这个节点里的消息内容（`OB11MessageMixType`） |
| `user_id` | str 或 int | | 该节点显示的 QQ 号，建议给一个 |
| `uin` | str 或 int | | 同上，go-cqhttp 兼容别名 |
| `name` | str | | 昵称的 go-cqhttp 兼容别名 |
| `id` / `source` / `summary` / `prompt` / `time` | str | | 一般不用填 |
| `news` | `[{text}]` | | 一般不用填 |

```json
[
  {"type": "node", "data": {"nickname": "甲", "user_id": "10001",
    "content": [{"type": "text", "data": {"text": "第一句"}}]}},
  {"type": "node", "data": {"nickname": "乙", "user_id": "10002",
    "content": [{"type": "text", "data": {"text": "第二句"}}]}}
]
```

> **整条消息必须全部是 `node`**。混进任何别的段（包括 `text`）→ 直接报错
> `转发消息不能和普通消息混在一起发送, 转发需要保证 message 只有 type 为 node 的元素`。

---

## 3. 发不出去的段（别用）

| type | 表现 | 原因 |
|---|---|---|
| `xml` | 段被丢弃 | 空实现 |
| `poke` | 段被丢弃 | 空实现；戳一戳要走独立的 `send_poke` 接口 |
| `miniapp` | 段被丢弃 | 空实现 |
| `onlinefile` | 段被丢弃 | 明确标注不需要支持发送 |
| `flashtransfer` | 段被丢弃 | 空实现 |
| `share` | **整条请求报错** | NapCat 的协议联合类型里**没有** `share` 这个段 |

> 前五个不会报错，只是白写；`share` 会让整条消息失败。

---

## 4. 冲突与互斥清单

| # | 约束 | 违反后果 |
|---|---|---|
| 1 | `node` 必须独占整条消息 | 整条报错 `转发消息不能和普通消息混在一起发送` |
| 2 | `music` 的「平台版」与「custom 版」互斥（`id` vs `url`/`image`） | 段被丢弃 |
| 3 | `image` / `record` / `video` / `file` 的 `file` 必填；给了 `url` 会覆盖 `file` | 缺 `file` → 段被丢弃 |
| 4 | `at` 在私聊无效 | 段被静默丢弃；整条只有 at 时整条报错 |
| 5 | `reply` 需要真实存在的消息 | 段被静默丢弃，消息照发 |
| 6 | 所有段都不支持或全部失败 | 整条报错 `消息体无法解析, 请检查是否发送了不支持的消息类型` |
| 7 | `record` 需要 FFmpeg 原生适配器转 SILK | 命令行适配器下抛 `convertToNTSilkTct is not implemented` |
| 8 | `markdown` / 平台版 `music` 需要签名服务 | 段被静默丢弃 |
| 9 | `dice` / `rps` 的 `result` 不算数 | 点数是服务端随机的 |
| 10 | `share` 不在协议里 | 整条报错 `未知的消息类型：share` |

**段之间没有其它互斥关系**：`text` / `face` / `image` / `at` / `reply` / `json` / `contact` / `dice` / `rps` / `location` 可以任意混排、任意重复、任意顺序。

---

## 5. 字段名陷阱

这几个是最容易写错的，`data` 里的键名必须一字不差：

| 想表达 | ❌ 常见错法 | ✅ 正确写法 |
|---|---|---|
| @ 某人 | `{"type":"at","data":{"user_id":"123"}}` | `{"type":"at","data":{"qq":"123"}}` |
| @ 全体 | `{"type":"at","data":{"qq":"all"}}` 之外的任何写法 | 就写 `"all"` |
| 引用回复 | `{"type":"reply","data":{"message_id":"7"}}` | `{"type":"reply","data":{"id":"7"}}` |
| 发图 | `{"type":"image","data":{"image":"/a.png"}}` | `{"type":"image","data":{"file":"/a.png"}}` |
| 发网络图 | 只给 `url`、不给 `file` | `{"type":"image","data":{"file":"https://..."}}`（或 `file` + `url` 都给） |
| 文本 | `{"type":"text","text":"hi"}`（少 `data`） | `{"type":"text","data":{"text":"hi"}}` |
| 商城表情 | 只给 `emoji_id` | 四个字段 `emoji_package_id` / `emoji_id` / `key` / `summary` 全给 |

另外注意：

- **`type` 的名字是 `image` 不是 `pic`/`picture`**，`record` 不是 `voice`/`audio`/`ptt`。
- **数值型字段别加引号**（`emoji_package_id`、`lat`、`lon`、`sub_type`、`seq`），字符串型别去引号（`qq`、`id`、`text`）。
- 段数组里**不能写 CQ 码**（`[CQ:at,qq=123]` 会被当普通文本发出去），要 @ 就发 `at` 段。

---

## 6. 常见组合示例

**纯文本**

```json
[{"type": "text", "data": {"text": "在的"}}]
```

**群聊：引用 + @ + 文本（交错顺序自由）**

```json
[
  {"type": "reply", "data": {"id": "746312745"}},
  {"type": "at",    "data": {"qq": "123456789"}},
  {"type": "text",  "data": {"text": " 你说的这个"}},
  {"type": "at",    "data": {"qq": "987654321"}},
  {"type": "text",  "data": {"text": " 也一起看看"}}
]
```

**图片 + 说明文字**

```json
[
  {"type": "image", "data": {"file": "/sdcard/DCIM/a.jpg"}},
  {"type": "text",  "data": {"text": "\n截图如上"}}
]
```

**系统表情 + 文本**

```json
[
  {"type": "face", "data": {"id": "14"}},
  {"type": "text", "data": {"text": " 笑死"}}
]
```

**合并转发（整条只能有 node）**

```json
[
  {"type": "node", "data": {"nickname": "甲", "user_id": "10001",
    "content": [{"type": "text", "data": {"text": "第一句"}}]}},
  {"type": "node", "data": {"nickname": "乙", "user_id": "10002",
    "content": [{"type": "text", "data": {"text": "第二句"}}]}}
]
```

**卡片（JSON 卡片）**

```json
[{"type": "json", "data": {"data": "{\"app\":\"com.tencent.xxx\"}"}}]
```

---

## 7. 自检清单

发送前按顺序过一遍：

1. 每个元素的 `type` 在 §1 / §2 的白名单里？不在 → 换掉。
2. 每个元素都有 `data` 对象？（不是把字段摊在 `data` 外面）
3. `data` 里的必填字段都在？（§1 / §2 表里的 ✅）
4. 有 `node` 的话，是不是**整条消息全是 `node`**？
5. 媒体类段是不是给了 `file`？（`url` / `path` 只是补充，`file` 必填）
6. 这段是不是私聊发 `at`？（私聊请删掉 `at` 段）
7. 是不是用了 §3 里那些发不出去的段？

---

## 8. 来源

- 段 zod schema：`napcat.mjs:71953-72300`，联合类型 `OB11MessageData`：`napcat.mjs:72229-72281`
- 发送侧转换表 `ob11ToRawConverters`：`napcat.mjs:73214-73504`
- 消息归一化（数组 / CQ 字符串）：`napcat.mjs:73970-73972`
- 文件类字段优先级 `url > file > path`：`napcat.mjs:73713-73728`
- 未知 type 报错：`napcat.mjs:73664`；整条为空的报错：`napcat.mjs:73679`
- `node` 独占校验：`napcat.mjs:74012`（`check()`）
- `at` 私聊丢弃：`napcat.mjs:73240`