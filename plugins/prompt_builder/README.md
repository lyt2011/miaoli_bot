# Prompt Builder

把 `state["prompts"]` 里的各个段拼成一条 `SystemMessage`，放到 `messages` 的**第一个位置**。

## 数据来源

`GraphState.prompts` 是一个 `Dict[str, str]`，它的状态通道（langgraph 的 state channel）是 `miaoli_bot.core` 的 `UntrackedSectionPatch`（`SectionPatch` 的子类，`checkpoint()` 返回 `MISSING`、不落盘）：

```python
prompts: Annotated[Dict[str, str], UntrackedSectionPatch]
```

各子插件往自己那段写，互不覆盖：

```python
return {"prompts": {"account-info": "..."}}   # account_injector（平级插件 miaoli_qq_channel 的子插件）写账号信息段
return {"prompts": {"soul": "你是喵璃"}}          # miaoli_bot_adapter 写人设段
return {"prompts": {"meme-helper": None}}     # 删掉 meme-helper 段
```

同一段重复写同一个值是幂等的 —— `UntrackedSectionPatch.update()` 用结构化对比判定变更，内容没变就不 bump 版本、不产生新 checkpoint。

## 工作流程

`build_prompt` 挂在 `on_before_request`（`priority=NORMAL`）：

1. **取段** —— 遍历 `state["prompts"]`，每段渲染成 `<key>\nvalue\n</key>`
2. **排序** —— 渲染好的段按**长度降序**排列（`sorted(..., key=len, reverse=True)`），最长的那段排在前面，保证同一组段每次拼出的串完全一致
3. **拼串** —— 段之间用 `\n\n` 连接
4. **幂等判断** —— 若 `messages[0]` 已经是 `SystemMessage` 且内容与拼出来的串相同，返回 `None`（不写任何增量，省掉一次 `Overwrite`）
5. **落位** —— 先滤掉历史里的 `SystemMessage`，再 `Overwrite([SystemMessage(串), *其余消息])`

## 为什么必须用 Overwrite

`messages` 的通道是 `add_messages`，它只会**追加**。直接返回 `{"messages": [SystemMessage(...)]}` 的结果是 `SystemMessage` 被追加到末尾：

```
实测：['HumanMessage', 'AIMessage', 'SystemMessage']   ← 错
期望：['SystemMessage', 'HumanMessage', 'AIMessage']
```

`Overwrite` 是 langgraph 官方的「绕过 reducer 直接写入」包装，用它才能整体替换。

## 与压缩的先后关系

`compact_if_need`（`base_nodes`，`priority=HIGH`）与 `build_prompt`（`NORMAL`）在**同一个事件** `ON_BEFORE_REQUEST` 上，`HIGH`(100) 严格高于 `NORMAL`(0)，所以每一轮都是先压缩、再拼装系统提示：

```
ON_BEFORE_REQUEST → compact_if_need（priority=HIGH：过门槛才压，Overwrite 拼回）
                  → time_inject（MEDIUM）
                  → build_prompt（NORMAL）→ pick_tools（LOW）
```

压缩的 `Overwrite` 只替换 `get_compaction_range` 求出的那段区间并保留区间外的原文，`build_prompt` 的 `Overwrite([SystemMessage, *messages])` 在它之后执行，因此插进去的系统提示不会被压缩冲掉。

## 与 account_injector 的分工

`account_injector` 不在主包的 `plugins/` 下，它由**平级插件** `miaoli_qq_channel`（`/sdcard/Ncatbot_QQ/plugins/miaoli_qq_channel`，独立仓库，自带 `account_injector` 与 `qq_platform_tools` 两个子插件）提供。

职责划分不变：`account_injector` 只负责**产出**（往 `prompts` 写 `account-info` 段），本插件只负责**组装与落位**。两者不抢同一个字符串键。

## 注册

```python
registry.on(ON_BEFORE_REQUEST, build_prompt, priority=NORMAL)
```

`registry` 内部是 `reverse=True` 排序，**priority 数值越大越先执行**。本插件用 `NORMAL`(0)，先于 `default_routing` 的默认跳转（`MINIMUM`）。

`tool_permission_manager` 的 `pick_tools` 用 `LOW`(-10)，严格低于本插件 —— 它摘的是工具表，与本插件写 `messages[0]` 互不干扰，先后不依赖插件加载顺序。
