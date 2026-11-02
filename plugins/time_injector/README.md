# Time Injector

每轮往 `state["prompts"]` 写一段 `current_time`，值是当前时间，格式 `年-月-日-小时-分钟-秒`。

## 产出

```python
return {"prompts": {"current_time": "2026-11-01-04-50-39"}}
```

`prompts` 是 `Dict[str, str]`，`prompt_builder` 会把它渲染成 `<current_time>...</current_time>` 放进系统提示词。

## 注册

```python
registry = get_handler_registry()
registry.on_turn_start(inject_current_time, priority=NORMAL + 1)
```

`on_close` 里对称摘除：

```python
registry.remove_turn_start(inject_current_time)
```

挂在 `ON_TURN_START`，保证每轮重新取时间 —— 挂在 `ON_BEFORE_REQUEST` 也只在一次请求内有效，但一轮里若有多步工具调用，`ON_TURN_START` 取到的是本轮开始的时刻。

## 时区

用 `datetime.now()`，跟宿主进程的本地时区走（容器 `/etc/timezone` = `Asia/Shanghai`）。要固定时区就得改成 `datetime.now(ZoneInfo("Asia/Shanghai"))`。
