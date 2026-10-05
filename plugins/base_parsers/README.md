两级解析链的解析器实现。

**事件解析器**（`EventParseChain`）
- `GroupMessageEventParser`：群聊事件元数据
- `PrivateMessageEventParser`：私聊事件元数据

**消息段解析器**（`SegmentParseChain`）
- `TextSegmentParser`：文本
- `AtSegmentParser`：@ 某人
- `QQImageSegmentParser`：图片（含 `is_meme` 表情包标记）
- `FileSegmentParser`：文件
- `ReplySegmentParser`：引用消息

两者都按注册顺序取第一个接受的解析器（短路），最终由 `utils.easier_parser.parse_message` 合并成 `ParseResult(event, segments)`。
