# miaoli_bot

**English** | [简体中文](../README.md)

An LLM-agent QQ bot plugin built on [Ncatbot](https://github.com/NapNeko/NcatBot) + [LangGraph](https://github.com/langchain-ai/langgraph).
A self-built graph pipeline feeds QQ conversations to any OpenAI-compatible endpoint, so every incoming message lets the model think, reply and call tools.

- **Version**: 0.49.0
- **Entry point**: `main.py` (plugin class `MiaoLiBot`)
- **Runtime host**: Ncatbot plugin system (NapCat / OneBot 11)
- **LLM client**: picked by `llm.providers[].client` — `ChatOpenAI` (`langchain-openai`) / `ChatDeepSeek` (`langchain-deepseek`) / `ChatAnthropic` (`langchain-anthropic`), all built through `miaoli_bot.api.build_client()`
- **Message entry**: **channels**. This package owns the abstraction (`BaseChannel` / `BaseChannelMessage` / `ChannelRegistry` / `ChannelSurface`) and registers no `@registrar.on_message` of its own. The QQ side — event capture, ring buffer, segment serialisation — lives in the sibling plugin [`miaoli_qq_channel`](../../miaoli_qq_channel) (independent repository) and hands its data over through `miaoli_bot.api.register_channel()`
- **Wake loop**: `on_startup` creates one long-lived `tick` task that `await`s the `RUN_REQUESTED` event with `tick.interval` (60 s by default) as its fallback timeout, so `api.please_run_graph()` wakes it early — N requests collapse into one wake-up, and a wake-up with nothing to drain returns without running the graph
- **Default routing**: in the edgeless topology "which event runs next" is declared by the handlers themselves. `default_routing` supplies the default hop for all eight events (**one node file per event**, each returning a single `Goto`), including the `ON_AFTER_REQUEST` branch (last message carries `tool_calls` → tool loop, otherwise → wrap up). It registers at the **lowest** priority `MINIMUM`, so any sub-plugin on a higher tier can preempt it and reroute or stop the turn

## Features

- 🧩 **Event pipeline (edgeless topology)**: `GraphPipeline` lives in this repo under `core/graph_pipeline/` (generic `GraphPipeline[StateT, ContextT, InputT, OutputT]`, TypeVars taken from `langgraph.typing`). The eight event constants and the `GRAPH_EVENTS` declaration order live in `consts/graph_events.py` — the first entry is where `START` lands. `wire(events)` adds one node per event plus a single entry edge and **defines no order**; nodes are attached **explicitly** with `register_handler(event, node, priority=0)`, and the handlers of one event run in descending `priority` (larger value first; the nine-tier ladder lives in `consts/node_priorities.py`: `MAXIMUM`(9999) / `HIGHEST`(1000) / `HIGH`(100) / `MEDIUM`(10) / `NORMAL`(0) / `LOW`(-10) / `LOWEST`(-100) / `TRIVIAL`(-1000) / `MINIMUM`(-9999)). Every handler receives the state **view** with the updates of the handlers before it already folded in, and answers with one of four shapes: a plain `dict` accumulates an update and lets the remaining handlers run, `Continue(updates=…)` accumulates and stops them, `Goto(goto=…, updates=…)` jumps to another event, `Abort(reason=…)` raises `AgentAborted` at the `ainvoke` call site. An exception inside one handler is logged and the handler is skipped — one broken node does not take the turn down with it
- 🔌 **Sub-plugin system**: `core.Loader` reads `sub_plugin.load_from` (`List[DirectoryPath]`, multiple directories allowed), builds a `Plugin` for every subdirectory containing `metadata.toml` (missing metadata raises, directories without `__init__.py` are skipped), then loads them in dependency order — "build the Python package → instantiate `entry_class` → inject `workspace` / `metadata` / `config` → `on_load()`". A failing plugin is unloaded and marked erred, and the plugins depending on it are skipped; unloading walks the same order backwards. Sub-plugins attach graph nodes with `HandlerRegistry.on(event, func, priority)`, tools with `miaoli_bot.api.register_tool()`, channels with `register_channel()` and store entries with `store_set()` — all four return an undo callable, which the plugin keeps in `self.undo_list` and calls from `on_close` (skipping that duplicates registrations on the next load). `config.yaml` is optional at the framework level: a plugin without one gets `self.config = None`, and every plugin that reads configuration validates it with pydantic in `on_load`, so a bad file fails loudly instead of degrading silently
- 🧠 **LLM access**: `main.py` only writes the drained payload into state. `miaoli_bot_adapter`'s `inject_soul` / `inject_output_protocol` nodes (`ON_TURN_START`, `priority=MEDIUM`) read `data/SOUL.md` and `data/output_protocol.md` from the sub-plugin's own directory into the `soul` / `output-protocol` sections of `prompts`; `base_nodes`' `build_client` (`priority=NORMAL`) then calls `miaoli_bot.api.build_client()` to create the client from the root config (the class comes from `llm.providers[].client`) into `runtime.context["client"]` — **deliberately without binding tools at construction**, because the tool table changes per request. `call_llm` binds `runtime.context["tool_surface"].tools` (a `ToolRegistry.to_surface()` snapshot) and calls the model, logging token usage with cache hits; `invoke_tools` runs the requested tools through `ToolNode`. The tool loop itself is routed by `default_routing`'s `on_after_request`
- 🗜️ **Context compaction (one node, one range)**: `compact_if_need` (`base_nodes`, on `ON_BEFORE_REQUEST` at `priority=HIGH`, so it runs before every other handler of that event) first gates on the model's real `context_window` / `max_tokens` — `Σ estimate_message_tokens(message) < context_window - max_tokens` returns `None` and issues no request at all; past the gate it asks `get_compaction_range(messages)` for a closed **compaction range**, hands that slice to `compact_now` to be summarized, and replaces `messages` wholesale with `Overwrite([*messages[:p_start], <summary>, *pruned slice, *messages[p_end + 1:]])`. The right edge always stops **just before the last run of consecutive `HumanMessage`s**, so the burst of messages a user sends in a group chat is never swallowed no matter what follows it (nothing, a tool round, or a plain reply); the left edge starts after the last `SystemMessage`, never on a `ToolMessage` and never backs off a `tool_calls` `AIMessage`, so no tool group is split and no tool result is orphaned. The compactor itself (`ChatHistory` / `TokenPruner` / `compact_now` / `estimate_message_tokens` / `extract_*` / `truncate_content_if_need`) and its prompt live in the main package under `core/compact/`; sub-plugins call it, they do not own it
- 📝 **Segmented prompt assembly**: `prompts` is not one big string but `Dict[str, str]` on an `UntrackedSectionPatch` channel — each sub-plugin writes its own section (`{"identity": …}` / `{"style": …}`), writing `None` deletes a section, and re-writing an unchanged value does not produce a new checkpoint. `prompt_builder`'s `build_prompt` node (`ON_BEFORE_REQUEST`, `priority=NORMAL`) renders every section as `<key>\nvalue\n</key>`, joins them longest-first, drops stale `SystemMessage`s and puts the result at `messages[0]` with `Overwrite`; if the string already equals the current first `SystemMessage` it returns `None` and writes nothing
- 📜 **State / runtime separation**: `models.GraphState` holds conversation state — `messages` (`add_messages`, checkpointed) and `prompts` (`UntrackedSectionPatch`, never checkpointed). `models.GraphRuntimeContext` holds per-invocation dependencies: `tool_surface`, `client` (written by `build_client`), plus optional `custom_status` / `custom_mapping`. `context` is not shallow-copied and keeps the original references, so non-serializable objects (LLM clients, locks) belong in `context` — putting them into state crashes at msgpack serialisation time
- 🎛️ **Typed configuration**: `PluginConfig` holds `llm` (an `LLMConfig` with `provider` / `model` — two names checked by `model_validator` against `providers` — plus `thinking_effort` (this project's reasoning-effort level) and `providers`, a `List[Provider]` where each entry has `name` / `base_url` / `api_key` / `client` (`openai` / `deepseek` / `anthropic`) / `models`; `models` is a `List[LLM]` with `name` / `context_window` / `max_tokens` / `support_visions` / `thinking_efforts`), `tick` (`interval`, default 60 s), `graph` (`atimeout`, default 60 s — the total timeout of one graph run), `checkpointer`, `sub_plugin` and `channel` (`atimeout`, default 30 s — the drain timeout). There is no `account` section any more: QQ ids and nicknames belong to the channel plugin, which injects them as the `account-info` section
- 🛠️ **Closed tool loop, non-uniform return values**: tools register through `ToolRegistry` and execute via `ToolNode`. The main package ships no tools at all — system / meme / web-search tools come from built-in sub-plugins, QQ platform tools from the channel plugin. Return shapes still differ: `read_file` / `write` / `replace` return strings, `read_image` returns an image block list (or an error string), `bash` returns `{"status": bool, "exit_code": …, "stdout": …}`, while meme and web-search tools return `{"status": bool, …}` / `{"results": …}`. `tool_permission_manager` layers a **global** allow / refuse table on top (`ON_BEFORE_REQUEST`, `priority=LOW`): it deletes every tool the table does not `allow`, so an undeclared tool is denied by default
- 🧩 **Channel abstraction instead of a message handler**: the message entry is `BaseChannel` (`name`, `platforms`, `async drain()`, `async reply(platform, thread_id, content)`) plus `BaseChannelMessage` (`thread_id`, `platform`, `to_content()`) from `protocols/channel/`; `Content` is `Union[str, List[Dict[str, Any]]]`, the same shape `to_content()` returns, so a reply can be a plain string or OpenAI-style blocks. `ChannelRegistry` registers channels by name idempotently and hands out a `ChannelSurface` snapshot; `batch_drain(atimeout)` runs every `drain()` concurrently under its own `wait_for` timeout and `gather(return_exceptions=True)`, so a slow or broken channel only spoils its own lane. `main.py` logs the exceptions and gets back a `{channel: [messages]}` mapping — one `drain()` hands back every thread that was buffered, one entry each; the messages are then run **one at a time** under their own `thread_id` (one `graph.atimeout` each) and the answer goes out through `channel.reply(message.platform, message.thread_id, last.content)` — whatever platform came in goes back out, and routing is never encoded into the `thread_id` string. Nothing in this package knows what a QQ message segment is: the event entry (`@registrar.on_message()`), the buffering and the segment handling all live in `miaoli_qq_channel`, which serialises whole events with `event._data.model_dump_json()` and crosses the boundary with plain JSON — there is no parse chain here any more, and the main package imports no ncatbot event or message model
- 🔍 **Web search**: the `web_search` sub-plugin registers exactly one `web_search` tool (**the tool name is backend-independent**) while `adapter` picks the backend — `langsearch` or `deepseek`, with `api_url` given in full because the plugin posts it itself. The raw response is handed to the model as-is; only the input schema and the response shape differ between backends. Failures come back as `{"message": "…"}` instead of raising, so the model can read the reason. Measured **English retrieval is clearly better than Chinese** (about 65% vs 30% relevance for technical/package queries), so the docstring asks the model to translate first. A separate `web-search-helper` prompt section (`inject_helper` on `ON_AGENT_START`) tells the model when a lookup is worth it, what `count` to use, and how to treat the results
- 🧩 **Intent recognition without touching the system prompt**: `intent_recognition` matches the last `HumanMessage` / `AIMessage` text against configured workflows (`ON_TURN_START`, `priority=NORMAL`) and appends **one** `HumanMessage` wrapped in `<intent-recognition>` with one `<name>…</name>` sub-tag per hit. Because the system prompt is left alone, its prefix cache survives; the rules inside one workflow are an **AND** relation (`all()`), and the four modes form a discriminated union keyed by `mode`: `single_keyword` (substring) / `any_keywords` (any hit) / `min_keywords` (at least `count` hits) / `regex` (`re.search`). Text extraction keeps only string blocks and dict blocks with a `str` `text` key, so base64 image data never reaches the matcher
- 🖼️ **Memes with a visible catalogue**: `meme_ops` registers `archive_qq_meme` / `send_meme_to_qq` / `remove_qq_meme_by_hash`, and on `ON_AGENT_START` (`priority=NORMAL`) injects `data/meme_helper.md` as the `meme-helper` section plus every archived meme as `hash: description: tags` lines into `available-memes`. The model therefore never spends a tool call enumerating memes — measured, that is what made it send a meme at all. Its README states the privacy risk plainly: the model may archive ordinary user images as memes
- 🔌 **External MCP servers**: `mcp_adapter` pulls tools from `stdio` / `streamable_http` MCP servers with `MultiServerMCPClient` and `add`s them into `runtime.context["tool_surface"]` on `ON_AGENT_START` (`priority=MEDIUM`). That ordering is load-bearing: `pick_tools` runs later and deletes everything not explicitly allowed, so MCP tools are invisible until they are granted a row. Servers marked `reusable: true` cache their tool list after the first fetch (until restart); the rest re-list every request
- 🩹 **Broken-history repair, two independent halves**: `pending_tool_fixer`'s `fix_pending_tool_call` and `orphan_tool_fixer`'s `fix_orphan_tool_message` both sit on `ON_REQUEST` (`priority=MEDIUM`) — the former synthesizes a `ToolMessage` for a `tool_calls` block that never got a result (full-table `Overwrite`), the latter deletes a `ToolMessage` whose request no longer exists (targeted `RemoveMessage` deletes). Both return `None` on a valid history, so nothing is written to `checkpoint_writes` on ordinary turns. They exist because an interrupted tool round poisons every following request with `400 insufficient tool messages following tool_calls`
- 🔧 **Protocols first**: every abstraction lives in `protocols/` and never in the layer that implements it — `PluginProtocol` (`on_load` / `on_close`), `BaseNodeAction` (common base of `Continue` / `Goto` / `Abort`), `BaseCheckpointerSaverAdapter` (`connect` / `close`) and `channel/{BaseChannel, BaseChannelMessage}`. The implementations stay where they belong: `core/plugin/`, `core/graph_pipeline/actions/`, `core/checkpointer_adapters/`, `core/notice_channel/`
- 🗄️ **Checkpointer adapter layer**: `checkpointer.database` switches checkpoint storage between `memory` / `sqlite` / `postgresql` — the three adapters under `core/checkpointer_adapters/` unify `InMemorySaver` / `AsyncSqliteSaver` / `AsyncPostgresSaver` behind one facade (`BaseCheckpointerSaverAdapter`: 1:1 forwarding of `BaseCheckpointSaver`'s sync / async protocol methods, `connect(connect_to, **extra)` to open, `close()` to release). `main.py`'s `CPA_MAPPING` picks the class by `database`, `on_load` injects it into the graph, `on_close` closes it
- 💾 **Shared store**: `core/SHARE_STORE` (defined in `core/share_store.py`, public name) is a global container with `set` / `drop` / `clear` / `recall` / `contains` / `is_empty` / `keys` / `values`; the twelve core keys live in `consts/share_store_keys.py` (`NCATBOT_API` / `RAW_CONFIG` / `PLUGIN_CONFIG` / `PLUGIN_DIR` / `WORKSPACE_DIR` / `GRAPH_PIPELINE` / `TOOL_REGISTRY` / `HANDLER_REGISTRY` / `INVOKE_LOCKS` / `CHANNEL_REGISTRY` / `MAIN_READY` / `RUN_REQUESTED`), and every sub-plugin uses keys under its own namespace (e.g. `miaoli_bot_adapter`'s `PLUGIN_CONFIG` / `RAW_CONFIG` / `WORKSPACE`, the channel plugin's `miaoli_qq_channel/…`). `api.store_set` warns when it overwrites an existing key — that warning exists to catch two sub-plugins fighting over one key; a caller that legitimately refreshes the same key every round passes `overwrite=True` and gets no warning
- 🚪 **`api/` facade**: sub-plugins never touch `SHARE_STORE` directly; they take everything from `miaoli_bot.api`, one module per concern — `config_ops` (`get_root_config`) / `llm_ops` (`build_client` / `get_model_info` / `get_provider_info`) / `sync_ops` (`get_invoke_lock` / `wait_main_ready` / `please_run_graph`) / `platform_ops` (`get_ncatbot_api`) / `registry_ops` (`get_handler_registry`) / `tool_ops` (`register_tool`) / `channel_ops` (`register_channel`) / `store_ops` (`store_recall` / `store_set` / `store_contains`), with `safe_run_graph` re-exported from `core` and `easier_send` from `utils.sugar`. `__all__` has exactly those 16 names. Key names, lookup paths and types stay locked inside the facade, and the three registration helpers return undo callables
- 🔁 **Wake task**: `main.py` owns one `tick` task instead of a `Job`. Each round it does `await wait_for(RUN_REQUESTED.wait(), timeout=tick.interval)` (a `TimeoutError` is just the fallback), `clear()`s the flag **before** running the graph (so requests arriving mid-run are kept for the next round), then drains every channel and runs the drained messages **serially** (each with its own `thread_id`, one `graph.atimeout` each), answering through `channel.reply(message.platform, message.thread_id, last.content)`. The task is created in `on_startup` together with a done-callback that logs a death **and restarts it**, but only while `MAIN_READY` is set — `on_close` clears that flag first, so a death during shutdown stays quiet instead of resurrecting the loop.
- 🧹 **Import blocks and alignment**: the imports at the top of a module are grouped as `__future__` → third-party `from` (one block per top-level package) → cross-package self references `miaoli_bot.x` → same-package relative imports `.` / `..` → stdlib `from` → plain `import`, with a blank line between blocks and shorter statements first inside a block. Columns are aligned to the next multiple of 4 after the longest prefix in the group (tab stop = 4), and **a multi-line import closes its group** — it aligns with the lines above it, while the lines below start a new group. Sub-plugins import from exactly one layer of the main package (`miaoli_bot.api` / `core` / `models` / `consts` / `utils` / `protocols`)
- 🎭 **Persona and output protocol live outside the core**: the main package holds no prompt assets at all — there is no `data/prompts/`, no root-config `prompt_file`, no `api.get_prompt`. The persona (`plugins/miaoli_bot_adapter/data/SOUL.md`) and the output protocol (`plugins/miaoli_bot_adapter/data/output_protocol.md`) are assets of the `miaoli_bot_adapter` sub-plugin, re-read from disk every turn; the `account-info` section is produced by the channel plugin's `account_injector`, never by this package
- 🧪 **Local tests**: `tests/` is committed; `pytest.ini` sets `pythonpath = ..` so `plugins/` lands on `sys.path`, `testpaths = tests` so a bare `pytest` works, and `asyncio_mode = auto` so `async def test_*` needs no marker. Current coverage is the pure parts: `PluginConfig` validation, the priority ladder, `SHARE_STORE`, the `ToolRegistry` / `ToolSurface` pair, and the `utils` writers

## Architecture

```
QQ / NapCat (OneBot 11)
        │ @registrar.on_message()
        ▼
miaoli_qq_channel (sibling plugin)     EventBuffer (deque, newest first, overflow drops the oldest)
        │ QQChannel(BaseChannel).drain() → List[BaseChannelMessage] (one per thread_id: thread_id / platform / to_content()) → one turn per message
        ▼
main.py  MiaoLiBot(NcatBotPlugin)      ← config.yaml → models.PluginConfig (llm / tick / graph / checkpointer / sub_plugin / channel)
        │   ① tick task: awaits RUN_REQUESTED, fallback tick.interval (60 s by default)
        │   ② channel_registry.to_surface().batch_drain(atimeout=channel.atimeout)
        │   ③ one message per thread → its own thread_id → serial graph runs (graph.atimeout each)
        ▼
miaoli_bot.core.GraphPipeline.ainvoke({"messages": [HumanMessage(to_content())]}, thread_id=<from the message>, context=…)
        │  safe_run_graph: INVOKE_LOCKS[thread_id] → ainvoke → last AIMessage → channel.reply(...)
        │
        │  START
        ▼
   ON_AGENT_START ── inject_mcp_tools (mcp_adapter, MEDIUM: external tools → tool_surface)
        │            inject_doc / inject_memes (meme_ops, NORMAL: meme-helper / available-memes sections)
        │            helper_inject (time_injector, NORMAL: time-inject-helper section)
        ▼
   ON_TURN_START ── inject_soul / inject_output_protocol (miaoli_bot_adapter, MEDIUM)
        │            recognize_intent (intent_recognition, NORMAL: one tagged HumanMessage)
        │            build_client (base_nodes, NORMAL: root config → context["client"])
        │            default_routing → ON_BEFORE_REQUEST
        ▼
   ON_BEFORE_REQUEST ── compact_if_need (base_nodes, HIGH: gated, Overwrite merges the range back)
        │               time_inject (time_injector, MEDIUM: interval-gated <time-inject> at the tail)
        │               build_prompt (prompt_builder, NORMAL: sections → SystemMessage at messages[0])
        │               pick_tools (tool_permission_manager, 1: drop tools not marked allow)
        ▼
   ON_REQUEST ── fix_pending_tool_call / fix_orphan_tool_message (MEDIUM, only act on broken history)
        │        call_llm (base_nodes, NORMAL: bind_tools → model → AIMessage)
        ▼
   ON_AFTER_REQUEST ── default_routing: on_after_request (does the last message carry tool_calls?)
        │
        ├─ yes ──▶ ON_TOOL_CALLING ── invoke_tools (ToolNode → ToolMessage)
        │                            └── back to ON_TURN_START (another round)
        │
        └─ no  ──▶ ON_TURN_END ──▶ ON_AGENT_END ── output_checker (LOW: Abort unless messages[-1] is an AIMessage)
                                              │    default_routing on_agent_end → Goto(END)
                                              ▼
                                             END

        │  final state: the last AIMessage is read and logged by main.py
        │  nothing is sent automatically — a reply must be a tool call
        ▼
send_message_to_qq (channel plugin tool) / send_meme_to_qq (meme_ops)  ──▶  QQ
```

Every hop drawn above comes from a handler returning `Goto`; the plain arrows that are not labelled with a plugin are `default_routing`'s defaults. Remove that plugin and the graph stops after the first event, because a node whose handlers all return plain updates has no next hop and langgraph treats it as the end.

### Directory structure

```
miaoli_bot/
├── main.py                        # plugin entry: MiaoLiBot (container + graph + sub-plugin loader + wake task)
├── manifest.toml                  # plugin manifest (name / version / entry_class / pip_dependencies / dependencies)
├── config.example.yaml            # config template (the real config.yaml is gitignored, it holds secrets)
├── __init__.py                    # empty on purpose: layering is enforced through the sub-packages
├── pytest.ini                     # pythonpath = .. / testpaths = tests / asyncio_mode = auto
├── api/                           # the only entry point for sub-plugins (facade, never exposes SHARE_STORE)
│   ├── __init__.py                #   __all__: 16 names
│   ├── channel_ops.py             #   register_channel (register a channel, returns an undo callable)
│   ├── config_ops.py              #   get_root_config
│   ├── llm_ops.py                 #   build_client / get_model_info / get_provider_info
│   ├── platform_ops.py            #   get_ncatbot_api (host runtime handle)
│   ├── registry_ops.py            #   get_handler_registry
│   ├── store_ops.py               #   store_recall / store_set / store_contains
│   ├── sync_ops.py                #   get_invoke_lock / wait_main_ready
│   └── tool_ops.py                #   register_tool (register a tool, returns an undo callable)
├── consts/                        # centralised constants
│   ├── graph_events.py            #   the 8 events + GRAPH_EVENTS (declaration order, first = START landing point)
│   ├── node_priorities.py         #   nine tiers (MAXIMUM 9999 … NORMAL 0 … MINIMUM -9999)
│   ├── id_prefix.py               #   session key prefixes (group- / private-)
│   └── share_store_keys.py        #   the 12 core SHARE_STORE keys
├── core/                          # framework layer
│   ├── share_store.py             #   ShareStore + the SHARE_STORE singleton
│   ├── graph_runner.py            #   safe_run_graph (INVOKE_LOCKS[thread_id] around ainvoke)
│   ├── handler_registry.py        #   HandlerRegistry.on(event, func, priority) → disposer
│   ├── compact/                   #   compact_now / ChatHistory / TokenPruner + consts/ runtimes/ utils/
│   ├── checkpointer_adapters/     #   in_memory_adapter.py / sqlite_adapter.py / postgresql_adapter.py
│   ├── graph_pipeline/            #   the graph pipeline itself
│   │   ├── graph_pipeline.py      #   GraphPipeline: wire / register_handler / bind / compile / ainvoke / _dispatch
│   │   ├── actions/               #   abort.py / continue_.py / goto.py
│   │   ├── channels/              #   section_patch.py / untracked_section_patch.py (per-key dict patch, None deletes)
│   │   └── runtimes/handler.py    #   Handler (event + priority + callable)
│   ├── notice_channel/            #   channel_registry.py (register / unregister / to_surface) + channel_surface.py (batch_drain)
│   ├── plugin/                    #   loader.py / plugin.py / plugin_entity.py + models/ + utils/ (topological sort)
│   └── tool/                      #   registry.py (ToolRegistry) + surface.py (ToolSurface)
├── data/                          # local prompt assets, gitignored (not part of the repository)
│   └── intent_prompts/            #   local private intent prompt texts (gitignored, not part of the repository)
├── errors/                        # exception definitions (AgentAborted / BaseBotError / BasePluginError / ClientNotFound /
│                                  #   EntryClassNotFound / MetadataMissingError / ModelNotFound / NotAPackageError /
│                                  #   ProviderNotFound / RepeatDependenceError)
├── models/                        # data models
│   ├── config/                    #   plugin_config / llm_config / tick_config / graph_config / channel_config / checkpointer_config / sub_plugin_config / provider_config
│   ├── graph_state.py             #   GraphState (messages checkpointed / prompts on an untracked channel)
│   └── graph_runtime_context.py   #   GraphRuntimeContext (tool_surface / client / custom_status / custom_mapping)
├── plugins/                       # 13 built-in sub-plugins (directories listed by sub_plugin.load_from)
│   ├── base_nodes/                #   build_client / compact_if_need / call_llm / invoke_tools / output_checker (nodes/ utils/ + README)
│   ├── default_routing/           #   one node file per event, 8 Goto defaults (nodes/ models/ config.example.yaml + README)
│   ├── intent_recognition/        #   rule matching → one tagged HumanMessage (models/rules/ models/workflows/ protocols/ + README)
│   ├── mcp_adapter/               #   MCP servers → tool_surface (models/transports/ protocols/ core/ nodes/ + README)
│   ├── meme_ops/                  #   meme tools + helper/catalogue sections (tools/ nodes/ core/ models/ data/ + README)
│   ├── miaoli_bot_adapter/        #   own config → store, SOUL.md / output_protocol.md → prompts (data/ nodes/ models/ consts/ config.example.yaml + README)
│   ├── orphan_tool_fixer/         #   delete ToolMessages without a request (nodes/ utils/ models/ + README)
│   ├── pending_tool_fixer/        #   synthesize results for dangling tool_calls (nodes/ utils/ models/ + README)
│   ├── prompt_builder/            #   prompts sections → SystemMessage at messages[0] (nodes/ utils/ + README)
│   ├── system_tools/              #   bash / read_file / write / replace / read_image (tools/ models/ + README)
│   ├── tool_permission_manager/   #   allow / refuse table, default deny (nodes/ models/ config.example.yaml + README)
│   └── web_search/                #   one web_search tool, langsearch / deepseek backends (tools/ models/ nodes/ + README)
├── protocols/                     # abstract base classes (sub-plugins depend on these, not on implementations)
│   ├── checkpointer_adapter.py    #   BaseCheckpointerSaverAdapter (connect / close + protocol forwarding)
│   ├── node_action.py             #   BaseNodeAction (common base of Continue / Goto / Abort)
│   ├── plugin.py                  #   PluginProtocol (on_load / on_close)
│   └── channel/                   #   channel.py (BaseChannel: name / platforms / drain / reply) + message.py (BaseChannelMessage: thread_id / platform / to_content, plus the Content alias)
├── tests/                         # pytest cases (committed)
└── utils/                         # helpers
    ├── config_ops.py              #   inject_workspace (expand the $workspace placeholder)
    ├── pipeline_helper.py         #   merge_into_updates / merge_into_state / is_none_action / is_update_action / apply_deltas
    └── sugar.py                   #   concatenate_id / easier_send
```

## Data flow

1. A QQ message travels NapCat → ncatbot → plugins. `miaoli_qq_channel` hooks `@registrar.on_message()` and records every private and group event into a ring buffer (newest first, the oldest is dropped when it is full); the main package registers no message handler at all.
2. `on_startup` prepares and loads the sub-plugins, creates the `tick` task and finally sets `MAIN_READY`. Each round that task either gets woken by `api.please_run_graph()` or times out after `tick.interval` (60 s by default); it clears the flag first (so a request arriving mid-run is kept for the next round), then takes a snapshot with `ChannelRegistry.to_surface()` and `batch_drain(atimeout=config.channel.atimeout)` drains every channel concurrently. A channel that raises or times out is logged and dropped from this round only.
3. What comes back is a `{channel: [messages]}` mapping — one `drain()` returns every thread that was buffered (one entry per thread = one turn). A message whose `to_content()` is empty (empty string or empty list; strings are then checked via `.strip()`) is dropped right there — no graph run for nothing. A message that only carries image blocks is **not** dropped — its `to_content()` is a list of blocks, not an empty value.
4. Every message runs `safe_run_graph({"messages": [HumanMessage(content)]}, {"tool_surface": tool_registry.to_surface()}, thread_id=message.thread_id)` — `content` is whatever `to_content()` returned (a plain string, or a list of content blocks); the session identity comes from the message itself, and the lock is the **per-`thread_id`** one from `INVOKE_LOCKS` (serial within a thread), and the tick itself runs messages one after another — concurrent runs smear the log into one lump and the framework formatter only prints `message`. The call returns the final state, the exception or the `AgentAborted`, and `tick` decides how to log each of the three.
5. `ON_AGENT_START` (in `GRAPH_EVENTS` order) runs `inject_mcp_tools` (`MEDIUM`) to add external MCP tools, then `meme_ops`' `inject_doc` / `inject_memes` (`NORMAL`) to write the `meme-helper` and `available-memes` sections, and finally `default_routing`'s `on_agent_start` (`MINIMUM`) hops to `ON_TURN_START`.
6. `ON_TURN_START` writes the persona and output protocol (`MEDIUM`), runs intent recognition (`NORMAL`, may append one tagged `HumanMessage`) and rebuilds the client (`NORMAL`) — one fresh client per round, tools bound later, per request. `default_routing`'s `on_turn_start` then hops to `ON_BEFORE_REQUEST`.
7. `ON_BEFORE_REQUEST` starts with **`compact_if_need`** (`base_nodes`, `priority=HIGH`): it estimates `sum(estimate_message_tokens(message) for message in messages)` against `context_window - max_tokens` and returns `None` below the threshold (no request issued); past it, `get_compaction_range(messages)` yields the closed range to compact, `core.compact.compact_now()` summarizes that slice, and `Overwrite` replaces history with `[..., before the range, <summary>, pruned slice, after the range, ...]`. The range never covers the trailing group of user messages or a `SystemMessage`, its first element is never a `ToolMessage`, and its last element is never a `tool_calls` `AIMessage`.
8. `ON_BEFORE_REQUEST` then runs `time_inject` (`MEDIUM`), renders `prompts` into `messages[0]` (`build_prompt`, `NORMAL`) and trims the tool table (`pick_tools`, `1`): only tools listed with `mode: "allow"` survive, everything else is deleted from the per-run `ToolSurface`.
9. `ON_REQUEST` first repairs a broken history if needed (`pending_tool_fixer` / `orphan_tool_fixer`, `MEDIUM`; both no-ops on valid history) and then calls the model (`call_llm`, `NORMAL`), appending the returned `AIMessage`.
10. `ON_AFTER_REQUEST` is the branch point: a last message with `tool_calls` jumps to `ON_TOOL_CALLING`, where `invoke_tools` runs them through `ToolNode` and appends the `ToolMessage`s, then back to `ON_TURN_START` for another round (the client is rebuilt, which is idempotent). Otherwise the turn wraps up through `ON_TURN_END` to `ON_AGENT_END`.
11. `ON_AGENT_END` runs `output_checker` at `LOW`: an `AIMessage` at `messages[-1]` passes, and an empty list, a `ToolMessage`, a `HumanMessage` or an unknown type each `Abort` with its own reason. `default_routing`'s `on_agent_end` (`MINIMUM`) then returns `Goto(END)`; `END` is filtered by langgraph, so there is no next hop.
12. The reply path is `channel.reply(message.platform, message.thread_id, messages[-1].content)` whenever the final state ends with an `AIMessage`. The main package never touches QQ: how a reply is delivered, and whether `\n\n` becomes several messages, is the channel's business. Send tools (`send_message_to_qq`, `send_meme_to_qq` through `miaoli_bot.api.easier_send()`) still exist for media, @-mentions, proactive messages and other conversations.
13. Plugin unload (`on_close`): first `MAIN_READY` is cleared ("no longer running", which keeps the `tick` task's done-callback quiet), then the task is cancelled and awaited — **the loop stops before the sub-plugins go away**, since it may be running the graph with their tools; then `await plugin_loader.unload_plugins()` runs in reverse dependency order (each `deactivate` forwards `on_close()`, then `unload()` clears `sys.modules`, so code edits take effect on reload) — **before** the containers are cleared, because sub-plugins need `HandlerRegistry` / `ToolRegistry` to detach their nodes, tools and channels; then `await self.cpa.close()` releases sqlite connections / the postgres pool (memory is a no-op); finally the known keys are dropped explicitly and leftovers only produce a warning.

## Built-in sub-plugins

The main package keeps the graph pipeline itself, the checkpointer adapter layer, the `HandlerRegistry` / `ToolRegistry` / `ChannelRegistry` registries (the last one handing out a per-run read-only `ChannelSurface`), the `core.Loader` framework; all business capability comes from sub-plugins. The thirteen built-in sub-plugins below live in this repo's `plugins/` directory; their `metadata.toml` and `config.example.yaml` templates are committed, while every deployment's real `config.yaml` is gitignored (root one included) and must be copied from the template before editing.

> The QQ side is **not** in this directory: [`miaoli_qq_channel`](../../miaoli_qq_channel) is a **separate plugin next to** `miaoli_bot` that depends on this package, registers its channel through `register_channel()`, and carries two sub-plugins of its own — `account_injector` (the `account-info` section) and `qq_platform_tools` (send message / download file / query message / recall / poke). The main package no longer owns either of them. Because they are loaded by `core.Loader` too, `sub_plugin.load_from` must list **both** plugin directories.

| Sub-plugin | Provides |
|---|---|
| `base_nodes` | The nodes the graph cannot run without: `build_client` (`on_turn_start`, `NORMAL`), `compact_if_need` (`on_before_request`, `HIGH`), `call_llm` (`on_request`, `NORMAL`), `invoke_tools` (`on_tool_calling`, `NORMAL`) and `output_checker` (`on_agent_end`, `LOW`). `compact_if_need` gates on the model's real `context_window` / `max_tokens`, then hands the range from `get_compaction_range` to `core.compact.compact_now` and merges the result back with `Overwrite`; the `SystemMessage`, the current user messages and any tool group outside the range survive untouched. `output_checker` uses `LOW` rather than `MINIMUM` so its `Abort` beats `default_routing`'s `Goto(END)` by priority instead of by registration order. Ships `README.md` |
| `default_routing` | The default hop for every event — eight node files, one `Goto` each, all registered at `MINIMUM`. It is what gives the edgeless graph an order; `enable: false` or removing it leaves the graph with no next hop after the first event. Ships `README.md` |
| `intent_recognition` | `recognize_intent` (`on_turn_start`, `NORMAL`) matches the last message's text against configured workflows and appends one `<intent-recognition>`-tagged `HumanMessage`; `state["prompts"]` is never touched, so the cached system prefix stays stable. Four rule modes (`single_keyword` / `any_keywords` / `min_keywords` / `regex`), rules inside one workflow are ANDed, workflows are keyed by `mode: "file"` and validated at load time. Ships `README.md` |
| `mcp_adapter` | `inject_mcp_tools` (`on_agent_start`, `MEDIUM`) pulls tools from `stdio` / `streamable_http` MCP servers via `MultiServerMCPClient` and adds them to the per-run `tool_surface`, deduplicating by name (`ToolSurface.add` overwrites). Runs before `pick_tools`, so MCP tools must be granted in the permission table. `reusable: true` caches a server's tool list until restart. Ships `README.md` |
| `meme_ops` | Three tools (`archive_qq_meme` / `send_meme_to_qq` / `remove_qq_meme_by_hash`) over a sqlite table, plus `inject_doc` and `inject_memes` (`on_agent_start`, `NORMAL`) writing the `meme-helper` and `available-memes` sections so the model can see the catalogue without an extra round. `enable: false` registers neither tools nor nodes. Ships `README.md`, including the privacy warning |
| `miaoli_bot_adapter` | Persona assets plus its own store entries: `on_load` validates its `config.yaml` and puts the raw dict, the validated config and its workspace path under its namespaced keys, while `inject_soul` / `inject_output_protocol` (`on_turn_start`, `MEDIUM`) re-read `data/SOUL.md` and `data/output_protocol.md` every turn into the `soul` / `output-protocol` sections. `enable: false` skips both nodes. Ships `config.example.yaml` and `README.md` |
| `orphan_tool_fixer` | `fix_orphan_tool_message` (`on_request`, `MEDIUM`) deletes `ToolMessage`s without an originating `tool_calls` block, emitting targeted `RemoveMessage` deletes only. `None` when the history is fine. Ships `README.md` |
| `pending_tool_fixer` | `fix_pending_tool_call` (`on_request`, `MEDIUM`) inserts a synthetic `ToolMessage` (`status="error"`, `id="auto-fix: …"`) after every `AIMessage` whose `tool_calls` never got a result, returning a full-table `Overwrite`; the `fix_message` text is configurable. Ships `README.md` |
| `prompt_builder` | `build_prompt` (`on_before_request`, `NORMAL`) joins the `prompts` sections into `<key>\nvalue\n</key>` blocks (longest first), drops stale `SystemMessage`s and writes `Overwrite([SystemMessage, *rest])`; returns `None` when the result equals the current first `SystemMessage`. Ships `README.md` |
| `system_tools` | Five tools: `bash` (command + encoding + timeout, own process group so a timeout kills the whole tree), `read_file`, `write`, `replace`, `read_image`. `read_image` filters by `support_image` **to restrict reading** — without it any path is base64-encoded into an image block and the request fails with `400`. Ships `config.example.yaml` and `README.md` |
| `time_injector` | Time injection: `helper_inject` (`on_agent_start`, `NORMAL`) writes how to read the `<time-inject>` tag into the `time-inject-helper` section of `prompts`; `time_inject` (`on_before_request`, `MEDIUM`) appends one `<time-inject>`-wrapped `HumanMessage` (`%Y-%m-%d %H:%M %z` plus an ISO weekday, time zone offset included, no seconds) to the tail of `messages`, throttled per conversation by `interval`. The time value **never** goes into `prompts` — it changes every round and would shatter the prefix cache of the whole request; only the static explanation lives there. `template` swaps in an external template file (`$now` / `$weekday`; a missing path silently falls back to the built-in template), and `config.yaml` is **mandatory** (a missing file makes `model_validate(None)` fail). Ships `config.example.yaml` and `README.md` |
| `tool_permission_manager` | `pick_tools` (`on_before_request`, `priority=LOW`) applies one global `allow` / `refuse` table and deletes everything else from `runtime.context["tool_surface"]`; an undeclared tool is denied, and `debug: true` only adds a warning. Identity no longer takes part in the decision. Ships `config.example.yaml` and `README.md` |
| `web_search` | Registers exactly one `web_search` tool; `adapter` picks `langsearch` (`POST /v1/web-search`) or `deepseek` (`POST /v1/tools/search`) and only changes the input schema and response shape. `api_url` is the full endpoint. Errors come back as `{"message": …}` rather than exceptions. Also registers `inject_helper` (`ON_AGENT_START`, `NORMAL`) which writes the usage notes into the `web-search-helper` prompt section (hard-coded in `consts/prompt.py`). Ships `README.md` |

Sub-plugin conventions: each directory holds a `metadata.toml` (`name` / `entry_class` / `description` / `dependences`; `entry_class` is a dotted path such as `main.MemeOps`) plus a committed `config.example.yaml` template (the real `config.yaml` is never committed). The entry class implements `PluginProtocol`, attaches graph nodes with `HandlerRegistry.on(event, func, priority)` and registers tools / channels / store entries with the matching `miaoli_bot.api` function in `on_load` — all of them returning undo callables that `on_close` calls before releasing anything else. A plugin that ships no `config.yaml` receives `self.config = None`, so anything that reads configuration validates it on load.

## Installation and usage

1. **Move this directory into the `plugins/` directory created by ncatbot** (e.g. `/root/Ncatbot_QQ/plugins/miaoli_bot`), and put `miaoli_qq_channel` **next to it** in the same `plugins/` directory — without a channel the graph has nothing to feed on. This is an ncatbot plugin, not a Python package, so **it is not installed with pip**; ncatbot scans `plugins/` on startup and loads any directory containing `manifest.toml`.
2. Make sure the runtime dependencies are installed (`manifest.toml`'s `pip_dependencies` are installed automatically when `plugin.auto_install_pip_deps` is enabled):
   - `ncatbot5` (`>=5.5.8`, import name `ncatbot`)
   - `langgraph` (`>=1.2.12`)
   - `langchain-core` (`>=1.6.5`): `@tool` definitions / `BaseMessage` / `BaseChatModel` and other base types
   - `langchain-openai` (`>=1.6.6`) / `langchain-deepseek` (`>=1.1.1`) / `langchain-anthropic` (`>=1.0.0`): the three client implementations, chosen by `llm.providers[].client`
   - `langgraph-checkpoint-sqlite` (`>=3.1.1`, used when `database: sqlite`)
   - `langgraph-checkpoint-postgres` (`>=3.1.2`, used when `database: postgresql`)
   - `aiosqlite` (`>=0.22.1`) / `psycopg` (`>=3.3.6`) / `psycopg-pool` (`>=3.3.3`): drivers and pools imported directly (`SQLiteAdapter` / `PostgresqlAdapter` / `MemeSqlite`)
   - `aiofiles` (`>=24.1.0`): async writes for `system_tools`' `write` / `replace`
   - `aiohttp` (`>=3.13.4`): HTTP client for `web_search` (`ClientSession`)
   - `pydantic` (`>=2.13.5`): config models (`models/config/`) and tool argument schemas
   - `pyyaml` (`>=6.0.3`): sub-plugin `config.yaml` parsing (`yaml.safe_load` in `core/plugin/plugin.py`)
   - `filetype` (`>=1.2.0`)
   - `langchain-mcp-adapters` (`>=0.3.2`): `mcp_adapter`'s `MultiServerMCPClient` (`langchain_mcp_adapters.client`)
   - `mcp` (`>=1.24.0`): the MCP protocol SDK, pulled in by the adapter above and declared explicitly here
3. Configure the plugin: `cp config.example.yaml config.yaml` and fill in a real `api_key` (`config.yaml` holds secrets and is gitignored). `on_load` starts with `PluginConfig.model_validate(self.config)`, so a missing required field, a nonexistent directory or a wrong type raises `ValidationError`, the plugin fails to load with a traceback in the log, and the rest of the bot is unaffected.
4. Start the bot. The wake task drains the channels and runs one graph per message every `tick.interval` (60 s by default), or earlier on `api.please_run_graph()`; the final `AIMessage` goes to `channel.reply(platform, thread_id, content)`.

Configuration keys map one-to-one onto the fields of `models.PluginConfig`:

| Key | Default / required | Purpose |
|---|---|---|
| `llm` | **required** | `LLMConfig`, everything model-side — the rows below are its sub-keys |
| `llm.provider` / `llm.model` | **required** | Which provider and which model to use — two names that `model_validator` checks against `llm.providers` |
| `llm.thinking_effort` | **required** | This project's reasoning-effort level: `off` / `minimal` / `low` / `medium` / `high` / `xhigh` / `max` / `ultra`, and it must be a key of the selected model's `thinking_efforts`. **Not consumed yet** — `build_client()` does not forward it to the client |
| `llm.providers` | **required** | `List[Provider]`, at least one entry; each is identified by its `name` field |
| `llm.providers[].name` | **required** | Provider name (the value of `llm.provider`) |
| `llm.providers[].base_url` | **required** | Request URL (**no path is appended**, so fill it up to the `/v1` level) |
| `llm.providers[].api_key` | **required** | Auth key |
| `llm.providers[].client` | **required** | Which client implementation to use: `openai` (`ChatOpenAI`) / `deepseek` (`ChatDeepSeek`, surfaces `reasoning_content`) / `anthropic` (`ChatAnthropic`) |
| `llm.providers[].models` | `[]` | `List[LLM]`; each is identified by its `name` field |
| `llm.providers[].models[].name` | **required** | Model name (the value of `llm.model`) |
| `llm.providers[].models[].context_window` | **required** | Context window, `>= 65535` |
| `llm.providers[].models[].max_tokens` | **required** | Maximum output tokens, `>= 2048` |
| `llm.providers[].models[].support_visions` | **required** | Modalities the model accepts, at least one of `image` / `video` / `text` / `audio` |
| `llm.providers[].models[].thinking_efforts` | **required** | `Dict[ThinkingEffort, str]`, at least one entry. A **"this project's level → what that provider actually calls it"** translation table: keys are limited to the eight levels above, values are free-form strings (providers disagree — DeepSeek's official API takes `minimal` / `low` / `medium` / `high` / `xhigh` / `max` / `ultra`, OpenAI only takes `minimal` / `low` / `medium` / `high`). **Not consumed yet.** Note that in YAML a key like `off` must be quoted — YAML 1.1 reads bare `off` / `on` / `yes` / `no` as booleans |
| `graph` | `GraphConfig()` | `atimeout` (seconds, default `60.0`) — the total timeout of one graph run; `tick` wraps every message in its own |
| `channel` | `ChannelConfig()` | `atimeout` (seconds, default `30.0`) — the per-channel timeout of `batch_drain` |
| `tick` | `TickConfig()` | `interval` (default `60.0`, must be `> 0`): the fallback wake interval in seconds for the `tick` task. `api.please_run_graph()` wakes it earlier; the interval only bounds how long an idle bot waits |
| `checkpointer` | `CheckpointerConfig()` | `database` (`memory` / `sqlite` / `postgresql`, default `memory`) / `connect_to` (database URL, **required unless `memory`**) / `extra` (extra kwargs passed straight to the adapter's `connect(**kwargs)`; postgresql understands `max_size` default 8 / `min_size` default 4 / `autocommit` default `true` / `row_factory` default `dict_row`). `on_load` picks the adapter from `CPA_MAPPING` by `database` and connects; `on_close` calls `close()` |
| `sub_plugin` | `SubPluginConfig()` | `load_from` (`List[DirectoryPath]`, empty by default; a missing directory fails validation with `path_not_directory` instead of blowing up later) and `enable` (default `false`, **currently unused** — `core.Loader` loads everything under `load_from`) |

### Local tests

```bash
cd <parent of the plugin>   # plugins/
<venv>/bin/python -m pytest miaoli_bot/tests/ -v
```

> `pytest.ini` lives at the plugin root: `pythonpath = ..` puts `plugins/` on `sys.path`, `testpaths = tests` makes a bare `pytest` hit the right directory, and `asyncio_mode = auto` lets async cases run directly. No `sys.path.insert` is needed inside the tests.

## Dependencies

| Package | Purpose |
|---|---|
| `ncatbot5` (`>=5.5.8`, import name `ncatbot`) | QQ bot framework / event and message APIs |
| `langgraph` (`>=1.2.12`) | Graph pipeline (`StateGraph` / `Command` / `Overwrite` / `ToolNode` / checkpoints) |
| `langchain-openai` (`>=1.6.6`) | `ChatOpenAI` (`client: openai`, any OpenAI-compatible endpoint) |
| `langchain-deepseek` (`>=1.1.1`) | `ChatDeepSeek` (`client: deepseek`); the only implementation that surfaces `reasoning_content` in `additional_kwargs` |
| `langchain-anthropic` (`>=1.0.0`) | `ChatAnthropic` (`client: anthropic`) |
| `langchain-core` (`>=1.6.5`) | `@tool` definitions, `BaseMessage` / `BaseChatModel` and other base types (used by the main package and sub-plugins alike) |
| `langgraph-checkpoint-sqlite` (`>=3.1.1`) | `AsyncSqliteSaver` (`checkpointer.database: sqlite`), bringing `aiosqlite` / `sqlite-vec` |
| `langgraph-checkpoint-postgres` (`>=3.1.2`) | `AsyncPostgresSaver` (`checkpointer.database: postgresql`), bringing `psycopg` / `psycopg-pool` |
| `aiosqlite` (`>=0.22.1`) | Async sqlite driver shared by `SQLiteAdapter` and `meme_ops.MemeSqlite` (connections closed by `close()` / `__aexit__`) |
| `aiofiles` (`>=24.1.0`) | Async disk writes for `system_tools`' `write` / `replace` (`aiofiles.open` + `async with`) |
| `aiohttp` (`>=3.13.4`) | Web search requests in `web_search` (`ClientSession.post`); also a transitive dependency of `ncatbot5`, declared explicitly here |
| `psycopg` (`>=3.3.6`) / `psycopg-pool` (`>=3.3.3`) | Driver and pool imported directly by `PostgresqlAdapter` (`AsyncConnectionPool`) |
| `pydantic` (`>=2.13.5`) | Config models (`BaseModel` / `Field` / `model_validator`) and tool argument schemas |
| `pyyaml` (`>=6.0.3`) | `yaml.safe_load` for sub-plugin `config.yaml` in `core/plugin/plugin.py` |
| `filetype` (`>=1.2.0`) | Image type sniffing in `system_tools` (`read_image`) |
| `langchain-mcp-adapters` (`>=0.3.2`) | `mcp_adapter`'s `MultiServerMCPClient` (fetch / call tools of external MCP servers) |
| `mcp` (`>=1.24.0`) | MCP protocol SDK (pulled in by `langchain-mcp-adapters`, declared explicitly so an upstream dependency change cannot cause an import-time `ModuleNotFoundError`) |

> `miaoli_qq_channel` needs `miaoli_bot` and nothing else; that dependency direction is one-way — this package never imports it.

## Project status

This section only describes **what the project is now**; it does not accumulate per release — see [`CHANGELOG.md`](../CHANGELOG.md) for what changed in each version.

**Current shape**

- The main package is the framework only: the graph pipeline (`core/graph_pipeline/`), the checkpointer adapter layer, the `HandlerRegistry` / `ToolRegistry` / `ChannelRegistry` registries, the `core.Loader` sub-plugin framework (the wake loop is `main.py`'s `tick` task), the `SHARE_STORE` container and the `api/` facade. Deployment is a plain directory sync — there is no extra local package to install
- All business logic comes from the **13** sub-plugins in this repo plus the QQ channel plugin next to it (see [Built-in sub-plugins](#built-in-sub-plugins)). Each ships its own `README.md` and a committed `config.example.yaml`; real `config.yaml` files are always gitignored and copied from the templates at deploy time
- The message path is: QQ event → channel plugin's ring buffer → `batch_drain` → one message per buffered thread → one graph per message, run serially, under the message's own `thread_id` → `channel.reply(message.platform, message.thread_id, last.content)`. Compaction, tool permissions, MCP integration, web search, memes and intent recognition are all wired in, each with an independent `enable` switch
- The LLM client can be `openai` / `deepseek` / `anthropic` (`llm.providers[].client`), all built through `miaoli_bot.api.build_client()`; `Provider` only describes *where to connect and which implementation to use*, while the client instance is rebuilt by `build_client` every round
- A message enters the graph as `HumanMessage(message.to_content(), additional_kwargs={"platform": message.platform})` — `to_content()` is the **only** model-input contract (a string, or a list of OpenAI-style content blocks); the platform rides along in `additional_kwargs` and goes back out through `channel.reply(...)` unchanged. Plain text for logs comes from the base class `__str__` (`<ClassName platform:thread_id>`), which must **never** call `to_content()` — after multimodal support that would be base64

**Known limitations**

- **The channel does not hand over multimodal content yet**: `to_content()` in `miaoli_qq_channel` still returns the whole event tree as a JSON string, so images exist only as NapCat `url` / `file_id` fields in text and the model has to fetch them itself; inlining them means turning them into base64 content blocks first. The main package side is ready — block lists go into `HumanMessage` untouched, and a message that only carries image blocks is no longer mistaken for an empty one
- **One `drain()` per channel also decides the fairness**: one call returns every buffered thread, but the still-serial graph runs make a single tick cost `N × graph.atimeout` in the worst case; and a channel that keeps its own queue can starve a thread if it never hands that one back
- **`\n\n` splitting is the channel's job**: the output protocol says "two newlines = two separate QQ messages", while `reply` only receives one `text`. The main package does not split; a channel that wants separate messages splits itself
- **No per-caller identity**: `thread_id` now reaches the graph, but nothing maps it to a person — permissions still degenerate to one global `allow` / `refuse` table; the earlier admin / white-list / passerby tiers are gone
- **Tools expose "who may use them", not "what they may do"**: the process runs as root and `tool_permission_manager` only controls tool visibility; once `bash` / `write` / `replace` are allowed there is no filesystem boundary
- **The permission table is a hard default-deny**: every new tool — including every dynamically named MCP tool — stays invisible until it gets its own `allow` row, and the log only repeats the warning per request
- **A range smaller than the retention budget makes compaction a net loss**: `compact_if_need` hard-codes `retain_tokens = 20000`, so `TokenPruner` keeps every line when the range holds fewer tokens than that — yet the summary is inserted anyway. When the range happens to be small while the total history is past the threshold, `messages` grows. A measured 5,864-token range produced a 5.6% end-to-end token increase
- **The threshold measures the whole history, not the range**: triggering depends on total tokens while what actually gets compacted is whatever `get_compaction_range` returns, and the two sizes are unrelated. A range larger than `context_window` stays over the limit after compaction and waits for the next round
- **Compaction is summaries of summaries**: the second compaction consumes the first one's output, so details erode as compaction repeats
- **Tool return values are not uniform**: `read_file` / `write` / `replace` return strings, `read_image` an image-block list, `bash` and the meme / web-search tools dicts. The model has to remember one shape per tool name and the prompt cannot describe them uniformly
- **Web search puts the whole response in context**: roughly 80% of a result payload is per-page body text, so a large `count` can eat a big part of the window at once; the default is deliberately conservative
- **`intent_recognition` can feed on its own injection**: `recognize_intent` runs on `ON_TURN_START` and tests only `messages[-1]`, but what it appends is a `HumanMessage` too. That event has two inbound edges — `on_agent_start` (a new user turn) and `on_tool_calling` (a loop-back with no new input). On a loop-back the last message may be the one just injected, or the one compaction kept, so the same turn matches and injects again; since compaction keeps the tail, the two feed each other and only langgraph's recursion limit stops it. When tool execution fails (`_dispatch` swallows the exception and no `ToolMessage` is produced) it adds one message per turn, permanently kept in the checkpoint
- **`intent_recognition` is pure string matching** on the last message's text only: no semantic understanding, and conditions that need earlier turns or tool results do not fit the `is_hit(data)` signature
