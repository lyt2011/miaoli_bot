# Prompt Builder

把 `state["prompts"]` 里的各个段拼成一条 `SystemMessage`，放到 `messages` 的**第一个位置**。

## 数据来源

`GraphState.prompts` 是一个 `Dict[str, str]`，它的状态通道（langgraph 的 state channel）是 `miaoli_bot.core` 的 `SectionPatch`：

```python
prompts: Annotated[Dict[str, str], SectionPatch]
```

各子插件往自己那段写，互不覆盖：

```python
return {"prompts": {"account-info": "..."}}   # account_injector（平级插件 miaoli_qq_channel 的子插件）写账号信息段
return {"prompts": {"soul": "你是喵璃"}}          # miaoli_bot_adapter 写人设段
return {"prompts": {"meme-helper": None}}     # 删掉 meme-helper 段
```

同一段重复写同一个值是幂等的 —— `SectionPatch.update()` 用结构化对比判定变更，内容没变就不 bump 版本、不产生新 checkpoint。

## 工作流程

`build_prompt` 挂在 `on_before_request`（`priority=NORMAL + 1`）：

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

`build_prompt` 的优先级比 `context_compactor` 的守卫高，但两者**不在同一个事件上** —— 压缩走的是独立的 `ON_BEFORE_COMPACT` / `ON_COMPACT` / `ON_AFTER_COMPACT` 三段，在 `ON_BEFORE_REQUEST` 之前：

```
ON_TURN_START → ON_BEFORE_COMPACT（守卫：压不压？）
              → 需要压：ON_COMPACT → ON_AFTER_COMPACT → 跳回 ON_TURN_START
              → 不需要压：直接到 ON_BEFORE_REQUEST
ON_BEFORE_REQUEST → build_prompt（priority=NORMAL+1）→ 其余节点
```

所以 `build_prompt` 每次到达 `ON_BEFORE_REQUEST` 时，`messages` 已经是压缩后的结果 —— 不会出现「刚插进去的 `SystemMessage` 被压缩的 `Overwrite` 冲掉」。

## 与 account_injector 的分工

`account_injector` 不在主包的 `plugins/` 下，它由**平级插件** `miaoli_qq_channel`（`/sdcard/Ncatbot_QQ/plugins/miaoli_qq_channel`，独立仓库，自带 `account_injector` 与 `qq_platform_tools` 两个子插件）提供。

职责划分不变：`account_injector` 只负责**产出**（往 `prompts` 写 `account-info` 段），本插件只负责**组装与落位**。两者不抢同一个字符串键。

## 注册

```python
registry.on(ON_BEFORE_REQUEST, build_prompt, priority=NORMAL + 1)
```

`registry` 内部是 `reverse=True` 排序，**priority 数值越大越先执行**。比 `NORMAL` 高一级，先于一切用 `NORMAL` 注册的处理器，也先于 `default_routing` 的默认跳转（`MINIMUM`）。

`tool_permission_manager` 的 `pick_tools` 注册的也是 `priority=1`，与本插件**同档** —— 同档按注册顺序（即插件加载顺序）执行，本插件不保证排在它前面。
