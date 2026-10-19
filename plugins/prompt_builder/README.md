# Prompt Builder

把 `state["prompt"]` 里的各个段拼成一条 `SystemMessage`，放到 `messages` 的**第一个位置**。

## 数据来源

`GraphState.prompt` 是一个 `Dict[str, str]`，通道是 `miaoli_pipeline` 的 `SectionPatch`：

```python
prompt: Annotated[Dict[str, str], SectionPatch]
```

各子插件往自己那段写，互不覆盖：

```python
return {"prompt": {"account_info": "..."}}    # account_injector 写账号信息段
return {"prompt": {"identity": "你是喵璃"}}    # 别的插件写人设段
return {"prompt": {"style": None}}            # 删掉 style 段
```

同一段重复写同一个值是幂等的 —— `SectionPatch.update()` 用结构化对比判定变更，内容没变就不 bump 版本、不产生新 checkpoint。

## 工作流程

`build_prompt` 挂在 `on_before_request`（`priority=NORMAL + 1`）：

1. **取段** —— 遍历 `state["prompt"]`，每段拼成 `<key>value</key>`
2. **拼串** —— 段之间用 `\n\n` 连接
3. **幂等判断** —— 若 `messages[0]` 已经是 `SystemMessage` 且内容与拼出来的串相同，返回 `None`（不写任何增量，省掉一次 `Overwrite`）
4. **落位** —— 先滤掉历史里的 `SystemMessage`，再 `Overwrite([SystemMessage(串), *其余消息])`

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

`account_injector` 只负责**产出**（往 `prompt` 写 `account_info` 段），本插件只负责**组装与落位**。两者不再抢同一个字符串键。

## 注册

```python
self.registry.on_before_request(build_prompt, priority=NORMAL + 1)
```

`register()` 内部是 `reverse=True` 排序，**priority 数值越大越先执行**。比 `NORMAL` 高一级，保证在 `pick_tools`（`priority=1`，同档按注册顺序）与 `base_topology` 的默认跳转（`MINIMUM`）之前跑完。
