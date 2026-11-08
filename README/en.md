# miaoli_bot

**English** | [简体中文](../README.md)

An LLM-agent QQ bot plugin built on [Ncatbot](https://github.com/NapNeko/NcatBot) + [LangGraph](https://github.com/langchain-ai/langgraph).
A self-built graph pipeline feeds QQ conversations to any OpenAI-compatible endpoint, so every incoming message lets the model think, reply and call tools.

- **Version**: 0.39.2
- **Entry point**: `main.py` (plugin class `MiaoLiBot`)
- **Runtime host**: Ncatbot plugin system (NapCat / OneBot 11)
- **LLM client**: picked by `providers[].client` — `ChatOpenAI` (`langchain-openai`) / `ChatDeepSeek` (`langchain-deepseek`) / `ChatAnthropic` (`langchain-anthropic`), all built through `miaoli_bot.api.build_client()`
- **Message entry**: **channels**. This package owns the abstraction (`BaseChannel` / `ChannelMessage` / `ChannelRegistry` / `ChannelSurface`) and registers no `@registrar.on_message` of its own. The QQ side — event capture, ring buffer, segment serialisation — lives in the sibling plugin [`miaoli_qq_channel`](../../miaoli_qq_channel) (independent repository) and hands its data over through `miaoli_bot.api.register_channel()`
- **Wake loop**: `on_startup` launches a `Job(run_graph, Every(timedelta(seconds=60)))`. Each tick drains every registered channel concurrently and runs the graph; a tick that finds nothing new returns without touching it
- **Default routing**: in the edgeless topology "which event runs next" is declared by the handlers themselves. `default_routing` supplies the default hop for all eleven events (**one node file per event**, each returning a single `Goto`), including the `ON_AFTER_REQUEST` branch (last message carries `tool_calls` → tool loop, otherwise → wrap up) and the compaction path (`ON_BEFORE_COMPACT` skips compaction and goes to `ON_BEFORE_REQUEST`; `ON_AFTER_COMPACT` jumps back to `ON_TURN_START`). It registers at the **lowest** priority `MINIMUM`, so any sub-plugin on a higher tier can preempt it and reroute or stop the turn

## Features

- 🧩 **Event pipeline (edgeless topology)**: `GraphPipeline` lives in this repo under `core/graph_pipeline/` (generic `GraphPipeline[StateT, ContextT, InputT, OutputT]`, TypeVars taken from `langgraph.typing`). The eleven event constants and the `GRAPH_EVENTS` declaration order live in `consts/graph_events.py` — the first entry is where `START` lands. `wire(events)` adds one node per event plus a single entry edge and **defines no order**; nodes are attached **explicitly** with `register_handler(event, node, priority=0)`, and the handlers of one event run in descending `priority` (larger value first; the nine-tier ladder lives in `consts/node_priorities.py`: `MAXIMUM`(9999) / `HIGHEST`(1000) / `HIGH`(100) / `MEDIUM`(10) / `NORMAL`(0) / `LOW`(-10) / `LOWEST`(-100) / `TRIVIAL`(-1000) / `MINIMUM`(-9999)). Every handler receives the state **view** with the updates of the handlers before it already folded in, and answers with one of four shapes: a plain `dict` accumulates an update and lets the remaining handlers run, `Continue(updates=…)` accumulates and stops them, `Goto(goto=…, updates=…)` jumps to another event, `Abort(reason=…)` raises `AgentAborted` at the `ainvoke` call site. An exception inside one handler is logged and the handler is skipped — one broken node does not take the turn down with it
- 🔌 **Sub-plugin system**: `core.Loader` reads `sub_plugin.load_from` (`List[DirectoryPath]`, multiple directories allowed), builds a `Plugin` for every subdirectory containing `metadata.toml` (missing metadata raises, directories without `__init__.py` are skipped), then loads them in dependency order — "build the Python package → instantiate `entry_class` → inject `workspace` / `metadata` / `config` → `on_load()`". A failing plugin is unloaded and marked erred, and the plugins depending on it are skipped; unloading walks the same order backwards. Sub-plugins attach graph nodes with `HandlerRegistry.on(event, func, priority)`, tools with `miaoli_bot.api.register_tool()`, channels with `register_channel()` and store entries with `store_set()` — all four return an undo callable, which the plugin keeps in `self.undo_list` and calls from `on_close` (skipping that duplicates registrations on the next load). `config.yaml` is optional at the framework level: a plugin without one gets `self.config = None`, and every plugin that reads configuration validates it with pydantic in `on_load`, so a bad file fails loudly instead of degrading silently
- 🧠 **LLM access**: `main.py` only writes the drained payload into state. `miaoli_bot_adapter`'s `inject_soul` / `inject_output_protocol` nodes (`ON_TURN_START`, `priority=NORMAL+1`) read `data/SOUL.md` and `data/output_protocol.md` from the sub-plugin's own directory into the `soul` / `output-protocol` sections of `prompts`; `base_nodes`' `build_client` (`priority=NORMAL`) then calls `miaoli_bot.api.build_client()` to create the client from the root config (the class comes from `providers[].client`) into `runtime.context["client"]` — **deliberately without binding tools at construction**, because the tool table changes per request. `call_llm` binds `runtime.context["tool_surface"].tools` (a `ToolRegistry.to_surface()` snapshot) and calls the model, logging token usage with cache hits; `invoke_tools` runs the requested tools through `ToolNode`. The tool loop itself is routed by `default_routing`'s `on_after_request`
- 🗜️ **Context compaction (three dedicated events)**: compaction is not an `if` buried in the request phase but three named graph events. `ON_BEFORE_COMPACT` hosts the **guard** `should_compact` (`context_compactor`, `priority=NORMAL`), which estimates tokens against `usage_tokens + max_tokens < context_window` — including the compaction prompt itself, since that prompt is appended to the request — and answers `Goto(ON_COMPACT)` or `Goto(ON_BEFORE_REQUEST)`. `ON_COMPACT` hosts **compaction** `compact`, which squeezes history into one `<abstract>` summary, keeps the tail (`compact.keep_count`, 20 in the shipped template, 5 in the model default; `ToolMessage`s do not consume quota so a `tool_calls` round is never cut in half) and replaces `messages` wholesale with `Overwrite`. The default hop on `ON_AFTER_COMPACT` goes **back to `ON_TURN_START`**, so the guard re-estimates the compacted history and normally lets the turn continue. Counting is configurable (`calculate.mode: base` = rough `chars × 0.7`, or `tiktoken` exact with an `encoder`); images are not counted by base64 length but folded into `图` placeholders derived from their pixel size; the prompt is built into `plugins/context_compactor/utils/prompt_ops.py` as `DEFAULT_PROMPT` and can be overridden with `compact.prompt_file`
- 📝 **Segmented prompt assembly**: `prompts` is not one big string but `Dict[str, str]` on a `SectionPatch` channel — each sub-plugin writes its own section (`{"identity": …}` / `{"style": …}`), writing `None` deletes a section, and re-writing an unchanged value does not produce a new checkpoint. `prompt_builder`'s `build_prompt` node (`ON_BEFORE_REQUEST`, `priority=NORMAL+1`) renders every section as `<key>\nvalue\n</key>`, joins them longest-first, drops stale `SystemMessage`s and puts the result at `messages[0]` with `Overwrite`; if the string already equals the current first `SystemMessage` it returns `None` and writes nothing
- 📜 **State / runtime separation**: `models.GraphState` holds conversation state — `raw_input` (`Annotated[str, UntrackedValue]`: visible within one `ainvoke`, **never persisted**), `messages` (`add_messages`, checkpointed) and `prompts` (`SectionPatch`, checkpointed). `models.GraphRuntimeContext` holds per-invocation dependencies: `tool_surface`, `client` (written by `build_client`), plus optional `custom_status` / `custom_mapping`. `context` is not shallow-copied and keeps the original references, so non-serializable objects (LLM clients, locks) belong in `context` — putting them into state crashes at msgpack serialisation time
- 🎛️ **Typed configuration**: `PluginConfig` holds `providers` (`List[Provider]`, each with `name` / `base_url` / `api_key` / `client` (`openai` / `deepseek` / `anthropic`) / `models`, where `models` is `List[LLM]` with `name` / `context_window` / `max_tokens` / `support_visions`), `provider` / `model` (checked by `model_validator` against `providers`), `checkpointer`, `sub_plugin` and `channel` (`drain_timeout`, default 30 s). There is no `account` section any more: QQ ids and nicknames belong to the channel plugin, which injects them as the `account-info` section
- 🛠️ **Closed tool loop, non-uniform return values**: tools register through `ToolRegistry` and execute via `ToolNode`. The main package ships no tools at all — system / meme / web-search tools come from built-in sub-plugins, QQ platform tools from the channel plugin. Return shapes still differ: `read_file` / `write` / `replace` return strings, `read_image` returns an image block list (or an error string), `bash` returns `{"status": bool, "exit_code": …, "stdout": …}`, while meme and web-search tools return `{"status": bool, …}` / `{"results": …}`. `tool_permission_manager` layers a **global** allow / refuse table on top (`ON_BEFORE_REQUEST`, `priority=1`): it deletes every tool the table does not `allow`, so an undeclared tool is denied by default
- 🧩 **Channel abstraction instead of a message handler**: the message entry is `BaseChannel` (`name`, `async drain()`) plus `ChannelMessage` (`raw`, `to_structured()`) from `protocols/channel/`. `ChannelRegistry` registers channels by name idempotently and hands out a `ChannelSurface` snapshot; `batch_drain(atimeout)` runs every `drain()` concurrently under its own `wait_for` timeout and `gather(return_exceptions=True)`, so a slow or broken channel only spoils its own lane. `main.py` logs the exceptions, drops empty channels, and `json.dumps` (indent 2) whatever is left into `raw_input`, also appending it as a single `HumanMessage`. Nothing in this package knows what a QQ message segment is: the event entry (`@registrar.on_message()`), the buffering and the segment handling all live in `miaoli_qq_channel`, which serialises whole events with `event._data.model_dump_json()` and crosses the boundary with plain JSON — there is no parse chain here any more, and the main package imports no ncatbot event or message model
- 🔍 **Web search**: the `web_search` sub-plugin registers exactly one `web_search` tool (**the tool name is backend-independent**) while `adapter` picks the backend — `langsearch` or `deepseek`, with `api_url` given in full because the plugin posts it itself. The raw response is handed to the model as-is; only the input schema and the response shape differ between backends. Failures come back as `{"message": "…"}` instead of raising, so the model can read the reason. Measured **English retrieval is clearly better than Chinese** (about 65% vs 30% relevance for technical/package queries), so the docstring asks the model to translate first
- 🧩 **Intent recognition without touching the system prompt**: `intent_recognition` matches the last `HumanMessage` / `AIMessage` text against configured workflows (`ON_TURN_START`, `priority=NORMAL`) and appends **one** `HumanMessage` wrapped in `<intent-recognition>` with one `<name>…</name>` sub-tag per hit. Because the system prompt is left alone, its prefix cache survives; the rules inside one workflow are an **AND** relation (`all()`), and the four modes form a discriminated union keyed by `mode`: `single_keyword` (substring) / `any_keywords` (any hit) / `min_keywords` (at least `count` hits) / `regex` (`re.search`). Text extraction keeps only string blocks and dict blocks with a `str` `text` key, so base64 image data never reaches the matcher
- 🖼️ **Memes with a visible catalogue**: `meme_ops` registers `archive_qq_meme` / `send_meme_to_qq` / `remove_qq_meme_by_hash`, and on `ON_AGENT_START` (`priority=NORMAL`) injects `data/meme_helper.md` as the `meme-helper` section plus every archived meme as `hash: description: tags` lines into `available-memes`. The model therefore never spends a tool call enumerating memes — measured, that is what made it send a meme at all. Its README states the privacy risk plainly: the model may archive ordinary user images as memes
- 🔌 **External MCP servers**: `mcp_adapter` pulls tools from `stdio` / `streamable_http` MCP servers with `MultiServerMCPClient` and `add`s them into `runtime.context["tool_surface"]` on `ON_AGENT_START` (`priority=MEDIUM`). That ordering is load-bearing: `pick_tools` runs later and deletes everything not explicitly allowed, so MCP tools are invisible until they are granted a row. Servers marked `reusable: true` cache their tool list after the first fetch (until restart); the rest re-list every request
- 🩹 **Broken-history repair, two independent halves**: `pending_tool_fixer`'s `fix_pending_tool_call` and `orphan_tool_fixer`'s `fix_orphan_tool_message` both sit on `ON_REQUEST` (`priority=NORMAL+2`) — the former synthesizes a `ToolMessage` for a `tool_calls` block that never got a result (full-table `Overwrite`), the latter deletes a `ToolMessage` whose request no longer exists (targeted `RemoveMessage` deletes). Both return `None` on a valid history, so nothing is written to `checkpoint_writes` on ordinary turns. They exist because an interrupted tool round poisons every following request with `400 insufficient tool messages following tool_calls`
- 🔧 **Protocols first**: every abstraction lives in `protocols/` and never in the layer that implements it — `PluginProtocol` (`on_load` / `on_close`), `BaseTimer` (`next_fire_time`), `BaseNodeAction` (common base of `Continue` / `Goto` / `Abort`), `BaseCheckpointerSaverAdapter` (`connect` / `close`) and `channel/{BaseChannel, ChannelMessage}`. The implementations stay where they belong: `core/plugin/`, `core/scheduler/timers/`, `core/graph_pipeline/actions/`, `core/check_pointer_adapters/`, `core/notice_channel/`
- 🗄️ **Checkpointer adapter layer**: `checkpointer.database` switches checkpoint storage between `memory` / `sqlite` / `postgresql` — the three adapters under `core/check_pointer_adapters/` unify `InMemorySaver` / `AsyncSqliteSaver` / `AsyncPostgresSaver` behind one facade (`BaseCheckpointerSaverAdapter`: 1:1 forwarding of `BaseCheckpointSaver`'s sync / async protocol methods, `connect(connect_to, **extra)` to open, `close()` to release). `main.py`'s `CPA_MAPPING` picks the class by `database`, `on_load` injects it into the graph, `on_close` closes it
- 💾 **Shared store**: `core/SHARE_STORE` (defined in `core/share_store.py`, public name) is a global container with `set` / `drop` / `clear` / `recall` / `contains` / `is_empty` / `keys` / `values`; the eleven core keys live in `consts/share_store_keys.py` (`NCATBOT_API` / `RAW_CONFIG` / `PLUGIN_CONFIG` / `PLUGIN_DIR` / `WORKSPACE_DIR` / `GRAPH_PIPELINE` / `TOOL_REGISTRY` / `HANDLER_REGISTRY` / `INVOKE_LOCK` / `CHANNEL_REGISTRY` / `MAIN_READY`), and every sub-plugin uses keys under its own namespace (e.g. `miaoli_bot_adapter`'s `PLUGIN_CONFIG` / `RAW_CONFIG` / `WORKSPACE`, the channel plugin's `miaoli_qq_channel/…`). `api.store_set` warns when it overwrites an existing key — that warning exists to catch two sub-plugins fighting over one key; a caller that legitimately refreshes the same key every round passes `overwrite=True` and gets no warning
- 🚪 **`api/` facade**: sub-plugins never touch `SHARE_STORE` directly; they take everything from `miaoli_bot.api`, one module per concern — `config_ops` (`get_root_config`) / `llm_ops` (`build_client` / `get_model_info` / `get_provider_info`) / `sync_ops` (`get_invoke_lock` / `wait_main_ready`) / `pipeline_ops` (`get_pipeline` / `safe_run_graph`) / `platform_ops` (`get_ncatbot_api`) / `registry_ops` (`get_handler_registry`) / `tool_ops` (`register_tool`) / `channel_ops` (`register_channel`) / `store_ops` (`store_recall` / `store_set` / `store_contains`), with `easier_send` re-exported from `utils.sugar`. `__all__` has exactly those 16 names. Key names, lookup paths and types stay locked inside the facade, and the three registration helpers return undo callables
- 🔁 **Scheduled wake loop**: `core/scheduler/` is a two-concept scheduler — `Job` (a coroutine plus a timer, unique `job_id`, `launch()` / `stop()` which refuse to double-start or double-stop unless called idempotently, and a one-shot `schedule()`) and the timers `Once` / `Every`. `main.py` owns a single `Job` running `run_graph` every 60 s; it is launched in `on_startup` after the sub-plugins are loaded and stopped in `on_close` before the container keys are dropped. `Job` logs and swallows handler exceptions, so a failed turn never kills the loop
- 🧹 **Import blocks and alignment**: the imports at the top of a module are grouped as `__future__` → third-party `from` (one block per top-level package) → cross-package self references `miaoli_bot.x` → same-package relative imports `.` / `..` → stdlib `from` → plain `import`, with a blank line between blocks and shorter statements first inside a block. Columns are aligned to the next multiple of 4 after the longest prefix in the group (tab stop = 4), and **a multi-line import closes its group** — it aligns with the lines above it, while the lines below start a new group. Sub-plugins import from exactly one layer of the main package (`miaoli_bot.api` / `core` / `models` / `consts` / `utils` / `protocols`)
- 🎭 **Persona and output protocol live outside the core**: the main package holds no prompt assets at all — there is no `data/prompts/`, no root-config `prompt_file`, no `api.get_prompt`. The persona (`plugins/miaoli_bot_adapter/data/SOUL.md`) and the output protocol (`plugins/miaoli_bot_adapter/data/output_protocol.md`) are assets of the `miaoli_bot_adapter` sub-plugin, re-read from disk every turn; the `account-info` section is produced by the channel plugin's `account_injector`, never by this package
- 🧪 **Local tests**: `tests/` is committed; `pytest.ini` sets `pythonpath = ..` so `plugins/` lands on `sys.path`, `testpaths = tests` so a bare `pytest` works, and `asyncio_mode = auto` so `async def test_*` needs no marker. Current coverage is the pure parts: `PluginConfig` validation, the priority ladder, and the `utils` writers

## Architecture

```
QQ / NapCat (OneBot 11)
        │ @registrar.on_message()
        ▼
miaoli_qq_channel (sibling plugin)     EventBuffer (deque, newest first, overflow drops the oldest)
        │ QQChannel(BaseChannel).drain() → QQChannelMessage.to_structured() → one JSON per event
        ▼
main.py  MiaoLiBot(NcatBotPlugin)      ← config.yaml → models.PluginConfig (providers / provider / model / checkpointer / sub_plugin / channel)
        │   ① Job(run_graph, Every(60s)) launched in on_startup
        │   ② channel_registry.to_surface().batch_drain(atimeout=channel.drain_timeout)
        │   ③ json.dumps(non-empty channels) → GraphState.raw_input + one HumanMessage
        ▼
miaoli_bot.core.GraphPipeline.ainvoke({"raw_input", "messages"}, thread_id="main", context=…)
        │  safe_run_graph: INVOKE_LOCK → ainvoke → last AIMessage / AgentAborted / Exception
        │
        │  START
        ▼
   ON_AGENT_START ── inject_mcp_tools (mcp_adapter, MEDIUM: external tools → tool_surface)
        │            inject_doc / inject_memes (meme_ops, NORMAL: meme-helper / available-memes sections)
        ▼
   ON_TURN_START ── inject_soul / inject_output_protocol (miaoli_bot_adapter, NORMAL+1)
        │            recognize_intent (intent_recognition, NORMAL: one tagged HumanMessage)
        │            build_client (base_nodes, NORMAL: root config → context["client"])
        ▼
   ON_BEFORE_COMPACT ── should_compact (context_compactor, NORMAL: estimate tokens)
        │                ├─ no compaction needed → straight on to ON_BEFORE_REQUEST
        │                └─ needs compaction → ON_COMPACT ── compact (summarize into <abstract>,
        │                                                    Overwrite replaces messages)
        │                                   └─▶ ON_AFTER_COMPACT ── back to ON_TURN_START
        ▼
   ON_BEFORE_REQUEST ── build_prompt (prompt_builder, NORMAL+1: sections → SystemMessage at messages[0])
        │               pick_tools (tool_permission_manager, 1: drop tools not marked allow)
        ▼
   ON_REQUEST ── fix_pending_tool_call / fix_orphan_tool_message (NORMAL+2, only act on broken history)
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
├── main.py                        # plugin entry: MiaoLiBot (container + graph + sub-plugin loader + 60s wake job)
├── manifest.toml                  # plugin manifest (name / version / entry_class / pip_dependencies / dependencies)
├── config.example.yaml            # config template (the real config.yaml is gitignored, it holds secrets)
├── __init__.py                    # empty on purpose: layering is enforced through the sub-packages
├── pytest.ini                     # pythonpath = .. / testpaths = tests / asyncio_mode = auto
├── api/                           # the only entry point for sub-plugins (facade, never exposes SHARE_STORE)
│   ├── __init__.py                #   __all__: 16 names
│   ├── channel_ops.py             #   register_channel (register a channel, returns an undo callable)
│   ├── config_ops.py              #   get_root_config
│   ├── llm_ops.py                 #   build_client / get_model_info / get_provider_info
│   ├── pipeline_ops.py            #   get_pipeline / safe_run_graph
│   ├── platform_ops.py            #   get_ncatbot_api (host runtime handle)
│   ├── registry_ops.py            #   get_handler_registry
│   ├── store_ops.py               #   store_recall / store_set / store_contains
│   ├── sync_ops.py                #   get_invoke_lock / wait_main_ready
│   └── tool_ops.py                #   register_tool (register a tool, returns an undo callable)
├── consts/                        # centralised constants
│   ├── graph_events.py            #   the 11 events + GRAPH_EVENTS (declaration order, first = START landing point)
│   ├── node_priorities.py         #   nine tiers (MAXIMUM 9999 … NORMAL 0 … MINIMUM -9999)
│   ├── id_prefix.py               #   session key prefixes (group- / private-)
│   └── share_store_keys.py        #   the 11 core SHARE_STORE keys
├── core/                          # framework layer
│   ├── share_store.py             #   ShareStore + the SHARE_STORE singleton
│   ├── graph_runner.py            #   safe_run_graph / _run_graph_with_lock (INVOKE_LOCK around ainvoke)
│   ├── handler_registry.py        #   HandlerRegistry.on(event, func, priority) → disposer
│   ├── check_pointer_adapters/    #   memory.py / sqlite.py / postgresql.py
│   ├── graph_pipeline/            #   the graph pipeline itself
│   │   ├── graph_pipeline.py      #   GraphPipeline: wire / register_handler / bind / compile / ainvoke / _dispatch
│   │   ├── actions/               #   abort.py / continue_.py / goto.py
│   │   ├── channels/              #   section_patch.py (per-key dict patch, None deletes)
│   │   └── runtimes/handler.py    #   Handler (event + priority + callable)
│   ├── notice_channel/            #   channel_registry.py (register / unregister / to_surface) + channel_surface.py (batch_drain)
│   ├── plugin/                    #   loader.py / plugin.py / plugin_entity.py + models/ + utils/ (topological sort)
│   ├── scheduler/                 #   job.py (Job) + timers/ (once.py / every.py)
│   └── tool/                      #   registry.py (ToolRegistry) + surface.py (ToolSurface)
├── data/                          # local prompt assets, gitignored (not part of the repository)
│   └── intent_prompts/            #   local private intent prompt texts (gitignored, not part of the repository)
├── errors/                        # exception definitions (AgentAborted / BaseBotError / BasePluginError / ClientNotFound /
│                                  #   EntryClassNotFound / MetadataMissingError / ModelNotFound / NotAPackageError /
│                                  #   ProviderNotFound / RepeatDependenceError)
├── models/                        # data models
│   ├── config/                    #   plugin_config / provider_config / sub_plugin_config / checkpointer_config / channel_setting
│   ├── graph_state.py             #   GraphState (raw_input untracked; messages / prompts checkpointed)
│   └── graph_runtime_context.py   #   GraphRuntimeContext (tool_surface / client / custom_status / custom_mapping)
├── plugins/                       # 13 built-in sub-plugins (directories listed by sub_plugin.load_from)
│   ├── base_nodes/                #   build_client / call_llm / invoke_tools / output_checker (nodes/ + README)
│   ├── context_compactor/         #   should_compact + compact (nodes/ utils/ models/ consts/ config.example.yaml + README)
│   ├── default_routing/           #   one node file per event, 11 Goto defaults (nodes/ models/ config.example.yaml + README)
│   ├── intent_recognition/        #   rule matching → one tagged HumanMessage (models/rules/ models/workflows/ protocols/ + README)
│   ├── mcp_adapter/               #   MCP servers → tool_surface (models/transports/ protocols/ core/ nodes/ + README)
│   ├── meme_ops/                  #   meme tools + helper/catalogue sections (tools/ nodes/ core/ models/ data/ + README)
│   ├── miaoli_bot_adapter/        #   own config → store, SOUL.md / output_protocol.md → prompts (data/ nodes/ models/ consts/ config.example.yaml + README)
│   ├── orphan_tool_fixer/         #   delete ToolMessages without a request (nodes/ utils/ models/ + README)
│   ├── pending_tool_fixer/        #   synthesize results for dangling tool_calls (nodes/ utils/ models/ + README)
│   ├── prompt_builder/            #   prompts sections → SystemMessage at messages[0] (nodes/ utils/ + README)
│   ├── system_tools/              #   bash / read_file / write / replace / read_image (tools/ models/ + README)
│   ├── tool_permission_manager/   #   allow / refuse table, default deny (nodes/ models/ config.example.yaml + README)
│   └── web_search/                #   one web_search tool, langsearch / deepseek backends (tools/ models/ + README)
├── protocols/                     # abstract base classes (sub-plugins depend on these, not on implementations)
│   ├── checkpointer_adapter.py    #   BaseCheckpointerSaverAdapter (connect / close + protocol forwarding)
│   ├── node_action.py             #   BaseNodeAction (common base of Continue / Goto / Abort)
│   ├── plugin.py                  #   PluginProtocol (on_load / on_close)
│   ├── timer.py                   #   BaseTimer (next_fire_time)
│   └── channel/                   #   channel.py (BaseChannel) + message.py (ChannelMessage)
├── tests/                         # pytest cases (committed)
└── utils/                         # helpers
    ├── config_ops.py              #   inject_workspace (expand the $workspace placeholder)
    ├── pipeline_helper.py         #   merge_into_updates / merge_into_state / is_none_action / is_update_action / apply_deltas
    └── sugar.py                   #   concatenate_id / easier_send
```

## Data flow

1. A QQ message travels NapCat → ncatbot → plugins. `miaoli_qq_channel` hooks `@registrar.on_message()` and records every private and group event into a ring buffer (newest first, the oldest is dropped when it is full); the main package registers no message handler at all.
2. `on_startup` prepares and loads the sub-plugins, launches the wake `Job` and finally sets `MAIN_READY`. From then on every 60 seconds `run_graph` waits for `MAIN_READY`, takes a snapshot with `ChannelRegistry.to_surface()` and `batch_drain(atimeout=config.channel.drain_timeout)` drains every channel concurrently. A channel that raises or times out is logged and dropped from this tick only.
3. The drained data is filtered (`{name: structured}` for the non-empty channels), `json.dumps(..., indent=2)` turns it into one string, and that string becomes both `GraphState.raw_input` and a single `HumanMessage` appended to `messages`. An empty tick returns right there.
4. `safe_run_graph({"raw_input": …, "messages": [HumanMessage(…)]}, thread_id="main", context={"tool_surface": tool_registry.to_surface()})` takes `INVOKE_LOCK`, calls `ainvoke` and returns the final state, or the exception, or the `AgentAborted` — `run_graph` only decides how to log the three cases.
5. `ON_AGENT_START` (in `GRAPH_EVENTS` order) runs `inject_mcp_tools` (`MEDIUM`) to add external MCP tools, then `meme_ops`' `inject_doc` / `inject_memes` (`NORMAL`) to write the `meme-helper` and `available-memes` sections, and finally `default_routing`'s `on_agent_start` (`MINIMUM`) hops to `ON_TURN_START`.
6. `ON_TURN_START` writes the persona and output protocol (`NORMAL+1`), runs intent recognition (`NORMAL`, may append one tagged `HumanMessage`) and rebuilds the client (`NORMAL`) — one fresh client per round, tools bound later, per request.
7. Compaction runs next, as its own three events. The guard either sends the turn straight to `ON_BEFORE_REQUEST` or into `ON_COMPACT`, whose `Overwrite` replaces `messages` with `[<abstract>, *kept tail]` (the old `SystemMessage` is restored at index 0 when `compact.recall_system_prompt` is on). `ON_AFTER_COMPACT` returns to `ON_TURN_START`, and the guard re-estimates the compacted history: below the threshold the turn continues, above it the turn compacts again.
8. `ON_BEFORE_REQUEST` renders `prompts` into `messages[0]` (`build_prompt`, `NORMAL+1`) and then trims the tool table (`pick_tools`, `1`): only tools listed with `mode: "allow"` survive, everything else is deleted from the per-run `ToolSurface`.
9. `ON_REQUEST` first repairs a broken history if needed (`pending_tool_fixer` / `orphan_tool_fixer`, `NORMAL+2`; both no-ops on valid history) and then calls the model (`call_llm`, `NORMAL`), appending the returned `AIMessage`.
10. `ON_AFTER_REQUEST` is the branch point: a last message with `tool_calls` jumps to `ON_TOOL_CALLING`, where `invoke_tools` runs them through `ToolNode` and appends the `ToolMessage`s, then back to `ON_TURN_START` for another round (the client is rebuilt, which is idempotent). Otherwise the turn wraps up through `ON_TURN_END` to `ON_AGENT_END`.
11. `ON_AGENT_END` runs `output_checker` at `LOW`: an `AIMessage` at `messages[-1]` passes, and an empty list, a `ToolMessage`, a `HumanMessage` or an unknown type each `Abort` with its own reason. `default_routing`'s `on_agent_end` (`MINIMUM`) then returns `Goto(END)`; `END` is filtered by langgraph, so there is no next hop.
12. The last `AIMessage` is logged by `run_graph`. **Nothing is sent automatically** — a reply only exists if the model called a send tool (`send_message_to_qq` from the channel plugin, `send_meme_to_qq` from `meme_ops`, which goes through `miaoli_bot.api.easier_send()`), which is also what `output_protocol.md` tells it.
13. Plugin unload (`on_close`): first `await plugin_loader.unload_plugins()` in reverse dependency order (each `deactivate` forwards `on_close()`, then `unload()` clears `sys.modules`, so code edits take effect on reload) — **before** the containers are cleared, because sub-plugins need `HandlerRegistry` / `ToolRegistry` to detach their nodes, tools and channels; then the wake job is stopped; then `await self.cpa.close()` releases sqlite connections / the postgres pool (memory is a no-op); finally the known keys are dropped explicitly and leftovers only produce a warning.

## Built-in sub-plugins

The main package keeps the graph pipeline itself, the checkpointer adapter layer, the `HandlerRegistry` / `ToolRegistry` / `ChannelRegistry` registries (the last one handing out a per-run read-only `ChannelSurface`), the `core.Loader` framework and the scheduler; all business capability comes from sub-plugins. The thirteen built-in sub-plugins below live in this repo's `plugins/` directory; their `metadata.toml` and `config.example.yaml` templates are committed, while every deployment's real `config.yaml` is gitignored (root one included) and must be copied from the template before editing.

> The QQ side is **not** in this directory: [`miaoli_qq_channel`](../../miaoli_qq_channel) is a **separate plugin next to** `miaoli_bot` that depends on this package, registers its channel through `register_channel()`, and carries two sub-plugins of its own — `account_injector` (the `account-info` section) and `qq_platform_tools` (send message / download file / query message / recall / poke). The main package no longer owns either of them. Because they are loaded by `core.Loader` too, `sub_plugin.load_from` must list **both** plugin directories.

| Sub-plugin | Provides |
|---|---|
| `base_nodes` | The four nodes the graph cannot run without: `build_client` (`on_turn_start`, `NORMAL`), `call_llm` (`on_request`, `NORMAL`), `invoke_tools` (`on_tool_calling`, `NORMAL`) and `output_checker` (`on_agent_end`, `LOW`). `output_checker` uses `LOW` rather than `MINIMUM` so its `Abort` beats `default_routing`'s `Goto(END)` by priority instead of by registration order. Ships `README.md` |
| `context_compactor` | Guard + compaction on two events: `should_compact` (`on_before_compact`, `NORMAL`) counts tokens against the model's real `context_window` / `max_tokens` (including the compaction prompt) and returns `Goto(ON_COMPACT)` or `Goto(ON_BEFORE_REQUEST)`; `compact` (`on_compact`, `NORMAL`) summarizes history into one `<abstract>` and returns `Overwrite`. Keep-count / prompt file / system-prompt restoration / counting mode are all configurable. Ships `README.md` |
| `default_routing` | The default hop for every event — eleven node files, one `Goto` each, all registered at `MINIMUM`. It is what gives the edgeless graph an order; `enable: false` or removing it leaves the graph with no next hop after the first event. Ships `README.md` |
| `intent_recognition` | `recognize_intent` (`on_turn_start`, `NORMAL`) matches the last message's text against configured workflows and appends one `<intent-recognition>`-tagged `HumanMessage`; `state["prompts"]` is never touched, so the cached system prefix stays stable. Four rule modes (`single_keyword` / `any_keywords` / `min_keywords` / `regex`), rules inside one workflow are ANDed, workflows are keyed by `mode: "file"` and validated at load time. Ships `README.md` |
| `mcp_adapter` | `inject_mcp_tools` (`on_agent_start`, `MEDIUM`) pulls tools from `stdio` / `streamable_http` MCP servers via `MultiServerMCPClient` and adds them to the per-run `tool_surface`, deduplicating by name (`ToolSurface.add` overwrites). Runs before `pick_tools`, so MCP tools must be granted in the permission table. `reusable: true` caches a server's tool list until restart. Ships `README.md` |
| `meme_ops` | Three tools (`archive_qq_meme` / `send_meme_to_qq` / `remove_qq_meme_by_hash`) over a sqlite table, plus `inject_doc` and `inject_memes` (`on_agent_start`, `NORMAL`) writing the `meme-helper` and `available-memes` sections so the model can see the catalogue without an extra round. `enable: false` registers neither tools nor nodes. Ships `README.md`, including the privacy warning |
| `miaoli_bot_adapter` | Persona assets plus its own store entries: `on_load` validates its `config.yaml` and puts the raw dict, the validated config and its workspace path under its namespaced keys, while `inject_soul` / `inject_output_protocol` (`on_turn_start`, `NORMAL+1`) re-read `data/SOUL.md` and `data/output_protocol.md` every turn into the `soul` / `output-protocol` sections. `enable: false` skips both nodes. Ships `config.example.yaml` and `README.md` |
| `orphan_tool_fixer` | `fix_orphan_tool_message` (`on_request`, `NORMAL+2`) deletes `ToolMessage`s without an originating `tool_calls` block, emitting targeted `RemoveMessage` deletes only. `None` when the history is fine. Ships `README.md` |
| `pending_tool_fixer` | `fix_pending_tool_call` (`on_request`, `NORMAL+2`) inserts a synthetic `ToolMessage` (`status="error"`, `id="auto-fix: …"`) after every `AIMessage` whose `tool_calls` never got a result, returning a full-table `Overwrite`; the `fix_message` text is configurable. Ships `README.md` |
| `prompt_builder` | `build_prompt` (`on_before_request`, `NORMAL+1`) joins the `prompts` sections into `<key>\nvalue\n</key>` blocks (longest first), drops stale `SystemMessage`s and writes `Overwrite([SystemMessage, *rest])`; returns `None` when the result equals the current first `SystemMessage`. Ships `README.md` |
| `system_tools` | Five tools: `bash` (command + encoding + timeout, own process group so a timeout kills the whole tree), `read_file`, `write`, `replace`, `read_image`. `read_image` filters by `support_image` **to restrict reading** — without it any path is base64-encoded into an image block and the request fails with `400`. Ships `config.example.yaml` and `README.md` |
| `tool_permission_manager` | `pick_tools` (`on_before_request`, `priority=1`) applies one global `allow` / `refuse` table and deletes everything else from `runtime.context["tool_surface"]`; an undeclared tool is denied, and `debug: true` only adds a warning. Identity no longer takes part in the decision. Ships `config.example.yaml` and `README.md` |
| `web_search` | Registers exactly one `web_search` tool; `adapter` picks `langsearch` (`POST /v1/web-search`) or `deepseek` (`POST /v1/tools/search`) and only changes the input schema and response shape. `api_url` is the full endpoint. Errors come back as `{"message": …}` rather than exceptions. Ships `README.md` |

Sub-plugin conventions: each directory holds a `metadata.toml` (`name` / `entry_class` / `description` / `dependences`; `entry_class` is a dotted path such as `main.MemeOps`) plus a committed `config.example.yaml` template (the real `config.yaml` is never committed). The entry class implements `PluginProtocol`, attaches graph nodes with `HandlerRegistry.on(event, func, priority)` and registers tools / channels / store entries with the matching `miaoli_bot.api` function in `on_load` — all of them returning undo callables that `on_close` calls before releasing anything else. A plugin that ships no `config.yaml` receives `self.config = None`, so anything that reads configuration validates it on load.

## Installation and usage

1. **Move this directory into the `plugins/` directory created by ncatbot** (e.g. `/root/Ncatbot_QQ/plugins/miaoli_bot`), and put `miaoli_qq_channel` **next to it** in the same `plugins/` directory — without a channel the graph has nothing to feed on. This is an ncatbot plugin, not a Python package, so **it is not installed with pip**; ncatbot scans `plugins/` on startup and loads any directory containing `manifest.toml`.
2. Make sure the runtime dependencies are installed (`manifest.toml`'s `pip_dependencies` are installed automatically when `plugin.auto_install_pip_deps` is enabled):
   - `ncatbot5` (`>=5.5.8`, import name `ncatbot`)
   - `langgraph` (`>=1.2.12`)
   - `langchain-core` (`>=1.6.5`): `@tool` definitions / `BaseMessage` / `BaseChatModel` and other base types
   - `langchain-openai` (`>=1.6.6`) / `langchain-deepseek` (`>=1.1.1`) / `langchain-anthropic` (`>=1.0.0`): the three client implementations, chosen by `providers[].client`
   - `langgraph-checkpoint-sqlite` (`>=3.1.1`, used when `database: sqlite`)
   - `langgraph-checkpoint-postgres` (`>=3.1.2`, used when `database: postgresql`)
   - `aiosqlite` (`>=0.22.1`) / `psycopg` (`>=3.3.6`) / `psycopg-pool` (`>=3.3.3`): drivers and pools imported directly (`SQLiteAdapter` / `PostgresqlAdapter` / `MemeSqlite`)
   - `aiofiles` (`>=24.1.0`): async writes for `system_tools`' `write` / `replace`
   - `aiohttp` (`>=3.13.4`): HTTP client for `web_search` (`ClientSession`)
   - `pydantic` (`>=2.13.5`): config models (`models/config/`) and tool argument schemas
   - `pyyaml` (`>=6.0.3`): sub-plugin `config.yaml` parsing (`yaml.safe_load` in `core/plugin/plugin.py`)
   - `filetype` (`>=1.2.0`)
   - `pillow` (`>=12.3.0`)
   - `tiktoken` (`>=0.14.0`)
   - `langchain-mcp-adapters` (`>=0.3.2`): `mcp_adapter`'s `MultiServerMCPClient` (`langchain_mcp_adapters.client`)
   - `mcp` (`>=1.24.0`): the MCP protocol SDK, pulled in by the adapter above and declared explicitly here
3. Configure the plugin: `cp config.example.yaml config.yaml` and fill in a real `api_key` (`config.yaml` holds secrets and is gitignored). `on_load` starts with `PluginConfig.model_validate(self.config)`, so a missing required field, a nonexistent directory or a wrong type raises `ValidationError`, the plugin fails to load with a traceback in the log, and the rest of the bot is unaffected.
4. Start the bot. Every 60 seconds the wake loop drains the channels and runs the graph; replies only happen through the model's send tools.

Configuration keys map one-to-one onto the fields of `models.PluginConfig`:

| Key | Default / required | Purpose |
|---|---|---|
| `provider` / `model` | **required** | Which provider and which model to use — two names that `model_validator` checks against `providers` |
| `providers` | **required** | `List[Provider]`, at least one entry; each is identified by its `name` field |
| `providers[].name` | **required** | Provider name (the value of `provider`) |
| `providers[].base_url` | **required** | Request URL (**no path is appended**, so fill it up to the `/v1` level) |
| `providers[].api_key` | **required** | Auth key |
| `providers[].client` | **required** | Which client implementation to use: `openai` (`ChatOpenAI`) / `deepseek` (`ChatDeepSeek`, surfaces `reasoning_content`) / `anthropic` (`ChatAnthropic`) |
| `providers[].models` | `[]` | `List[LLM]`; each is identified by its `name` field |
| `providers[].models[].name` | **required** | Model name (the value of `model`) |
| `providers[].models[].context_window` | **required** | Context window, `>= 65535` |
| `providers[].models[].max_tokens` | **required** | Maximum output tokens, `>= 2048` |
| `providers[].models[].support_visions` | **required** | Modalities the model accepts, at least one of `image` / `video` / `text` / `audio` |
| `channel` | `ChannelSetting()` | `drain_timeout` (seconds, default `30.0`) — the per-channel timeout of `batch_drain` |
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
| `pillow` (`>=12.3.0`) | Image dimension parsing in `context_compactor` (`image_to_tokens`, used to estimate image tokens) |
| `tiktoken` (`>=0.14.0`) | Exact token counting in `context_compactor` (`calculate.mode: tiktoken`) |
| `langchain-mcp-adapters` (`>=0.3.2`) | `mcp_adapter`'s `MultiServerMCPClient` (fetch / call tools of external MCP servers) |
| `mcp` (`>=1.24.0`) | MCP protocol SDK (pulled in by `langchain-mcp-adapters`, declared explicitly so an upstream dependency change cannot cause an import-time `ModuleNotFoundError`) |

> `miaoli_qq_channel` needs `miaoli_bot` and nothing else; that dependency direction is one-way — this package never imports it.

## Project status

This section only describes **what the project is now**; it does not accumulate per release — see [`CHANGELOG.md`](../CHANGELOG.md) for what changed in each version.

**Current shape**

- The main package is the framework only: the graph pipeline (`core/graph_pipeline/`), the checkpointer adapter layer, the `HandlerRegistry` / `ToolRegistry` / `ChannelRegistry` registries, the `core.Loader` sub-plugin framework, the scheduler that drives the wake loop, the `SHARE_STORE` container and the `api/` facade. Deployment is a plain directory sync — there is no extra local package to install
- All business logic comes from the **13** sub-plugins in this repo plus the QQ channel plugin next to it (see [Built-in sub-plugins](#built-in-sub-plugins)). Each ships its own `README.md` and a committed `config.example.yaml`; real `config.yaml` files are always gitignored and copied from the templates at deploy time
- The message path is: QQ event → channel plugin's ring buffer → `batch_drain` → one JSON payload → graph → tool loop → the model calls a send tool. Compaction, tool permissions, MCP integration, web search, memes and intent recognition are all wired in, each with an independent `enable` switch
- The LLM client can be `openai` / `deepseek` / `anthropic` (`providers[].client`), all built through `miaoli_bot.api.build_client()`; `Provider` only describes *where to connect and which implementation to use*, while the client instance is rebuilt by `build_client` every round

**Known limitations**

- **One conversation for everything**: `run_graph` hardcodes `thread_id="main"`, so every channel, group and private chat shares one checkpoint thread and one history. `utils.sugar.concatenate_id()` (the `group-` / `private-` prefixer) still exists, but nothing calls it any more
- **Replies are tool calls, not a return path**: the final `AIMessage` is only logged. If the model does not call a send tool, nobody receives anything — the send tools are what make the bot answer, and they live in the channel plugin
- **No per-caller identity**: one graph serves every channel, so no node knows who is speaking this round. Permissions therefore degenerate to one global `allow` / `refuse` table; the earlier admin / white-list / passerby tiers are gone
- **Tools expose "who may use them", not "what they may do"**: the process runs as root and `tool_permission_manager` only controls tool visibility; once `bash` / `write` / `replace` are allowed there is no filesystem boundary
- **The permission table is a hard default-deny**: every new tool — including every dynamically named MCP tool — stays invisible until it gets its own `allow` row, and the log only repeats the warning per request
- **Compaction is summaries of summaries, with no loop cap**: the second compaction consumes the first one's output, so details erode as compaction repeats. `ON_AFTER_COMPACT` goes back to `ON_TURN_START` and the guard simply re-estimates — if the compacted history still exceeds `context_window - max_tokens` (a long kept tail, or a large system prompt) the same turn compacts again, and only langgraph's recursion limit stops it
- **Tool return values are not uniform**: `read_file` / `write` / `replace` return strings, `read_image` an image-block list, `bash` and the meme / web-search tools dicts. The model has to remember one shape per tool name and the prompt cannot describe them uniformly
- **Web search puts the whole response in context**: roughly 80% of a result payload is per-page body text, so a large `count` can eat a big part of the window at once; the default is deliberately conservative
- **`intent_recognition` can feed on its own injection**: `recognize_intent` runs on `ON_TURN_START` and tests only `messages[-1]`, but what it appends is a `HumanMessage` too. That event has three inbound edges — `on_agent_start` (a new user turn), `on_tool_calling` and `on_after_compact` (loop-backs with no new input). On a loop-back the last message may be the one just injected, or the one compaction kept, so the same turn matches and injects again; since `compact` keeps the tail via `keep_recent`, the two feed each other and only langgraph's recursion limit stops it. When tool execution fails (`_dispatch` swallows the exception and no `ToolMessage` is produced) it adds one message per turn, permanently kept in the checkpoint
- **`intent_recognition` is pure string matching** on the last message's text only: no semantic understanding, and conditions that need earlier turns or tool results do not fit the `is_hit(data)` signature
