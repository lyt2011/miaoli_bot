本插件提供了表情包的数据库与发送扩展
但是需要注意: **大模型可能会将用户发送的普通图片归档为表情包，导致用户隐私被泄露**

## 配置

```yaml
enable: true

database:
  path: "/tmp/memes.db"

help_doc:
  path: "/sdcard/Ncatbot_QQ/plugins/miaoli_bot/plugins/meme_ops/data/meme_helper.md"
  encoding: "utf-8"
```

| 键 | 说明 |
| --- | --- |
| `enable` | 关闭时 `on_load` 直接返回，**工具与节点都不注册** |
| `database.path` | sqlite 数据库路径；启用时必填 |
| `help_doc.path` | 表情包扩展帮助文档，**绝对路径**；启用时必填 |
| `help_doc.encoding` | 读 `help_doc.path` 用的编码 |

`database.path` 与 `help_doc.path` 都是「可以关闭 + 不填，不能启用 + 不填」—— 启用时缺任一项，加载期直接 `ValueError`。

## 节点

| 节点 | 事件 / 优先级 | 产出 |
| --- | --- | --- |
| `inject_doc` | `on_agent_start`（`NORMAL`） | `prompts` 的 `meme_helper` 段，内容取自 `help_doc.path` 指向的文件 |
| `inject_memes` | `on_agent_start`（`NORMAL`） | `prompts` 的 `available_memes` 段，内容为所有已归档表情包的 `hash: description` 列表 |

提示词落在 `data/meme_helper.md`，由 `inject_doc` 在每次注入时读取（不做缓存）。放在文件里而不是常量里，是为了改提示词不用动代码。

## 为什么需要它

只把工具注册进工具表是不够的。`send_meme_to_qq` 需要一个 `hash`，模型手里没有，得先知道有什么 —— 多跑一轮工具循环。不提示的话模型不会为了一个表情包主动多跑这一轮，实测 6 条情绪化输入 0 条发图。

早先是让模型先调 `list_memes` 拿到清单再发，`inject_doc` 把「先查表再按情景 `send_meme_to_qq`」写成明确动作后，同样 6 条输入 6 条发图，且选中的表情包都与情景契合（累 → 摆烂、满分 → 竖拇指、被骂 → 生气炸毛、晚安 → 抱被子、笑 → 捶地、难过 → 摸头）。

现在清单由 `inject_memes` 直接拼进 `available_memes` 段常驻，不用再为「先看有什么」多跑一轮。

关键在于**先查表**：表里没货时模型自然不会发；表里有货且能直接看到，它就会挑一个发出去。

## 归档判据

`data/meme_helper.md` 里除了回复工作流，还有一段归档判据，要求模型在归档前逐条对照：

1. 是传递情绪的图片，还是普通图片（风景照 / 手机截图等）
2. 是否涉及用户隐私（账号密码 / IP 地址等）
3. 是否会引起争议（政治敏感等）
4. 是否存在不良文字 / NSFW 内容

并明确写了「**不能仅通过观察 image segment 的 `sub_type` 值来判断是否需要归档**」—— 用户以普通图片形式发送、但内容满足全部条件的图片，同样应该归档。

实测 5 个场景 × 2 次：负例（擦边 / IP 隐私 / 普通截图）6/6 全部正确不归档，正例 3/4 归档。唯一失分是 `sub_type=0` 的真表情包，1/2 归档 —— 提示词结尾「可以归档也可以不归档，完全基于人物设定」这句授权与「合格就归档」存在对冲。
