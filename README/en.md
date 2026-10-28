# miaoli_bot

**English** | [简体中文](../README.md)

An LLM-agent QQ bot plugin built on [Ncatbot](https://github.com/NapNeko/NcatBot) + [LangGraph](https://github.com/langchain-ai/langgraph).
A self-built graph pipeline feeds QQ conversations to any OpenAI-compatible endpoint, so each incoming message drives the model to think, reply, and call tools.

- **Version**: 0.30.2
- **Entry point**: `main.py` (plugin class `MiaoLiBot`)
- **Runtime host**: Ncatbot plugin system (NapCat / OneBot protocol)
- **LLM client**: `ChatOpenAI` from `langchain-openai` (`base_url` can point at any OpenAI-compatible endpoint)
- **Stage**: plugin split is done; the project is in an **optimization** phase — see [Project status](#project-status)
- **Default routing**: in the edgeless topology, "which event runs next" is declared by the handlers themselves. The `base_topology` sub-plugin supplies the default order (**one node file per event**, each returning a single `Goto`), handles the `ON_AFTER_REQUEST` branch (last message has `tool_calls` → tool loop, otherwise → wrap up), and backs the three compaction events (`ON_BEFORE_COMPACT` skips compaction by default and goes to `ON_BEFORE_REQUEST`; `ON_AFTER_COMPACT` jumps back to `ON_TURN_START`). It registers at the **lowest** priority `MINIMUM`, so any sub-plugin on any higher tier can preempt it and reroute or stop the turn

## Features

- 🧩 **Event pipeline (edgeless topology, extracted into its own package)**: `GraphPipeline` comes from the standalone dependency [`miaoli_pipeline`](https://github.com/lyt2011/miaoli_pipeline) (generic `GraphPipeline[StateT, ContextT, InputT, OutputT]`, TypeVars taken from `langgraph.typing`); this repo keeps only the event names and the registration facade — the 11 graph-event constants live in `consts/graph_events.py`, and nodes are attached **explicitly** with `register_handler(event, node, priority=0)` (multiple handlers per event, executed in descending `priority`, larger value first; tier constants are the nine-step ladder in `consts/node_priorities.py`: `MAXIMUM`(9999) … `NORMAL`(0) … `MINIMUM`(-9999)). `wire()` **defines no event order** — it only attaches event nodes plus one entry edge (`START → ON_AGENT_START`). Which event runs next is decided by handlers **actively returning a jump instruction**: `return {...}` accumulates an update and continues with the remaining handlers of the same event, `Continue(updates=…)` stops them, `Goto(goto=…, updates=…)` jumps to another event, and `Abort(reason=…, updates=…)` aborts the whole turn. **Which sub-plugin hooks which event, and where it jumps, is declared at registration time.**
- 🔌 **Sub-plugin system**: `core.Loader` reads `sub_plugin.load_from` (`List[Path]`, multiple directories allowed), builds a `Plugin` for every subdirectory containing `metadata.toml` (missing metadata raises, non-package directories are skipped), then in `tp_sort()` dependency order runs "register as a Python package → instantiate `entry_class` → inject `workspace` / `metadata` / `config` → `on_load()`". A failing `on_load` is logged and the plugin is dropped from `sys.modules`. Sub-plugins attach graph nodes via `HandlerRegistry.on_*()` and register tools via `ToolRegistry.register()`; on unload they detach everything in `on_close` with the matching `HandlerRegistry.remove_*()` / `ToolRegistry.remove()` (skipping this duplicates registrations on the next load). Unloading runs `deactivate()` (forwards `on_close`) → `unload()` (clears `sys.modules`), so code edits take effect on reload.
- 🧠 **LLM access**: `main.py` only writes `event` into state. The `miaoli_bot_adapter` sub-plugin's `inject_model_info` node (`ON_TURN_START`, `priority=NORMAL+1`) copies `base_url` / `api_key` / `model` / `max_tokens` from the root config into state; `inject_soul` at the same priority writes the persona file (`prompt_file`) into the `soul` section of `prompts`. Then `build_client` (`priority=NORMAL`) creates a `ChatOpenAI` from those four values into `runtime.context["client"]` (**deliberately without binding tools at construction** — the tool table changes per identity and per request). `call_llm` binds `runtime.context["tools"]` (from `ToolRegistry`) and calls the model. The tool loop is routed by `base_topology`'s `on_after_request`: if the last message carries `tool_calls`, jump to `ON_TOOL_CALLING` to execute the tools and return to `ON_TURN_START` for another round; otherwise jump to `ON_TURN_END`.
- 🗜️ **Context compaction (three dedicated events)**: compaction is no longer an `if` buried in `on_before_request` but three named events on the graph — `ON_BEFORE_COMPACT` hosts the **guard** `should_compact` (`context_compactor` sub-plugin, `priority=NORMAL`) which estimates tokens against the threshold: compact → `Goto(ON_COMPACT)`, otherwise → `Goto(ON_BEFORE_REQUEST)`; `ON_COMPACT` hosts **compaction** `compact`, which squeezes history into a single `<abstract>` summary and replaces it wholesale with `Overwrite`; the default jump on `ON_AFTER_COMPACT` goes **back to `ON_TURN_START`**, so the turn restarts and this time the guard sees the `<abstract>` marker and `Abort`s. Thresholds derive from the model's real `context_window` / `max_tokens` (reserving room for output); keep-count, prompt, and counting mode (`base` rough estimate or `tiktoken` exact) are all configurable, and the prompt lives in `plugins/context_compactor/data/compact_prompt.md`.
- 📝 **Segmented prompt assembly**: `prompts` is not one big string but `Dict[str, str]` — each sub-plugin writes its own section (`{"identity": …}` / `{"style": …}`), and writing `None` deletes a section. The `prompt_builder` sub-plugin's `build_prompt` node (`ON_BEFORE_REQUEST`, `priority=NORMAL+1`) joins all sections as `<key>value</key>` and puts the result at `messages[0]` with `Overwrite`; if the content equals the existing first `SystemMessage`, it returns `None` and skips the write.
- 📜 **State / runtime separation**: `models.GraphState` (conversation state: `messages` via `add_messages`, `prompts` via `SectionPatch`, both **checkpointed**; the six keys `event` / `model` / `base_url` / `api_key` / `max_tokens` / `final_answer` use `Annotated[T, UntrackedValue]` — visible within a single `ainvoke`, **never persisted**) is kept apart from `models.GraphRuntimeContext` (per-invocation dependencies: `client` / `tools`). `context` is not shallow-copied and keeps original references, so non-serializable objects (LLM clients, locks) must go into `context` — putting them in state crashes at msgpack serialization time.
- 🎛️ **Typed configuration**: `PluginConfig` holds `providers` (`List[Provider]`, each with `name` / `base_url` / `api_key` / `protocol` / `models`, where `models` is `List[LLM]` with `name` / `context_window` / `max_tokens` / `support_visions`), `provider` / `model` (validated by `model_validator` to exist in `providers`), `account` (`bot_id` / `admin_id` / `bot_nickname` / `admin_nickname`, all four required), `split`, `typing`, `checkpointer`, `sub_plugin`, plus `prompt_file` / `prompt`.
- 🛠️ **Closed tool loop**: tools register through `ToolRegistry`, execute via `ToolNode`, and always return a `{"status": bool, ...}` dict. The main package ships no tools at all — platform, system, meme, and web-search tools are all registered by built-in sub-plugins; `tool_permission_manager` layers per-identity tool permissions on top (`on_before_request` trims `runtime.context["tools"]`; undeclared tools are denied).
- 🔍 **Web search**: the `web_search` sub-plugin registers one `web_search` tool (**the tool name is backend-independent**) while `adapter` picks the backend — the request URL comes from each plugin's `config.yaml` `api_url` (the template ships `https://api.langsearch.com/v1/web-search` for langsearch); the raw response is handed to the model as-is. `adapter` only affects the input schema and the response shape, never the tool name. Measured **English retrieval is clearly better than Chinese** (about 65% vs 30% relevance for technical/package queries), so the docstring asks the model to prefer English queries.
- 🖼️ **Tool attachment fallback**: some models reject multimodal blocks inside `tool` messages (any block type yields `400` or is silently ignored). The `tool_attachment_fixer` sub-plugin's `fix_tool_attachment` node (`ON_TOOL_CALLING`, `priority=NORMAL-2`) moves a **non-string** `ToolMessage.content` into a following `HumanMessage` and replaces the original body with `replace_text`; it only applies to models declared in `models` and returns `None` when nothing changes.
- 🧩 **Two-level parse chains**: `EventParseChain` (group / private event metadata) and `SegmentParseChain` (text / AT / image / file / reply segments) dispatch separately, invoked by `event_adapter` in the `ob11_adapter` sub-plugin; the parsers **consume plain dicts** and import no ncatbot classes.
- 🖼️ **Multiple message segment types**: `text` → `{text}`, `at` → `{at}`, `image` → `{image, size, sub_tp}`, `file` → `{file, size}`, `reply` → `{reply}`; parsers dispatch on the segment's `type`.
- 🔧 **Protocols first**: `protocols/abc/` defines compile-time abstractions (`PluginProtocol` / `ChainProtocol` / `StoreProtocol` / `BaseCheckpointerSaverAdapter`).
- 🗄️ **Checkpointer adapter layer**: `checkpointer.database` switches checkpoint storage between `memory` / `sqlite` / `postgresql` — the three adapters under `adapters/check_pointers/` unify `InMemorySaver` / `AsyncSqliteSaver` / `AsyncPostgresSaver` behind one facade (`protocols.BaseCheckpointerSaverAdapter`: 1:1 forwarding of `BaseCheckpointSaver`'s sync/async protocol methods, `connect(connect_to, **extra)` to open, `close()` to release). `main.py`'s `CPA_MAPPING` picks the class by `database`, `on_load` injects it into the graph, `on_close` closes it.
- 💾 **Shared store**: `stores/SHARE_STORE` is a global container; core keys live in `consts/share_store_keys.py` (`NCATBOT_API` / `RAW_CONFIG` / `PLUGIN_CONFIG` / `PLUGIN_DIR` / `GRAPH_PIPELINE` / `WORKSPACE_DIR` / `TOOL_REGISTRY` / `HANDLER_REGISTRY`, 8 in total), and sub-plugins use their own namespaced keys (e.g. `ob11_adapter`'s `EVENT_PARSER` / `SEGMENT_PARSER` / `REGISTRY`).
- 🚪 **`api/` facade**: sub-plugins never touch `SHARE_STORE` directly; they take everything from `miaoli_bot.api` — account info (`get_admin_id` etc.), store operations (`store_recall` / `store_set` / `store_drop` / `store_update`), runtime handles (`get_ncatbot_api`), registry handles (`get_handler_registry` / `get_tool_registry`), config-derived values (`get_model_info` / `get_provider_info` / `get_prompt`), and send wrappers (`easier_send` etc.). Key names, lookup paths, and types stay locked inside the facade; sub-plugins depend on function signatures only.
- 🔔 **Priority yielding**: `on_message` registers at `priority=-100`, sitting in the post-processing position — extension plugins can take a message earlier and stop propagation (e.g. `miaoli_like`'s `赞我` uses `priority=100`); messages intercepted upstream never reach the LLM.
- 🎭 **Role play**: ships a catgirl persona prompt for "Miaoli" (`data/prompts/prompt_v1.7.md`, with historical v1.0 ~ v1.6), and the `account_injector` sub-plugin's `inject_account` node merges the persona with admin/bot QQ numbers and nicknames into the system prompt.
- ⏱️ **Output splitting and typing delay**: `on_message` splits the reply per root config `split` (`enable` / `delimiter`), skipping empty chunks; when `typing.enable` is on, each chunk sleeps `len(chunk) * uniform(base_speed ± speed_offset)` before sending, simulating a human typing. Sending is `main.py`'s job: in group chats the first chunk goes via `event.reply` (quoted), while the remaining chunks — and **every chunk in private chats** — go via `easier_send`.
- 🧪 **Local tests (to be rewritten)**: the cases in `tests/` (gitignored, not committed) targeted the old pi bridge layer and were invalidated wholesale by the 0.8.0 refactor.

## Architecture

```
QQ / NapCat (OneBot)
        │ ncatbot events
        ▼
main.py  MiaoLiBot(NcatBotPlugin)      ← config.yaml → models.PluginConfig (providers / provider / model / account / split / typing / sub_plugin / …)
        │   ① event._data.model_dump() + concatenate_id → session_id (thread_id)
        │   ② group chats must also @ the bot_id, otherwise skipped
        ▼
miaoli_pipeline.GraphPipeline.ainvoke({"event"}, thread_id=session_id, context=…)
        │
        │  START
        ▼
   ON_AGENT_START ── event_adapter (ob11_adapter: parse event → event_data, write back state["event"], append JSON to messages)
        │            inject_account (account info block → the account_info section of prompts)
        ▼
   ON_TURN_START ── inject_model_info (root config → base_url / api_key / model / max_tokens) + inject_soul (root config → the soul section)
        │            build_client (those four values → ChatOpenAI → context["client"])
        ▼
   ON_BEFORE_COMPACT ── should_compact (estimate tokens against threshold)
        │                ├─ no compaction needed ─────────────────┐
        │                └─ needs compaction → ON_COMPACT ── compact (squeeze into <abstract>,
        │                                                   Overwrite replaces messages)
        │                               └─▶ ON_AFTER_COMPACT ── back to ON_TURN_START
        ▼◀───────────────────────────────────────────────────────┘
   ON_BEFORE_REQUEST ── build_prompt (prompts sections → SystemMessage at messages[0]) → pick_tools (trim tools by identity)
        ▼
   ON_REQUEST ── call_llm ──▶ bind_tools(tools) → ChatOpenAI
        │                                              │
        │                                              ▼
   ON_AFTER_REQUEST ── base_topology: on_after_request (does the last message carry tool_calls?)
        │
        ├─ yes ──▶ ON_TOOL_CALLING ── invoke_tools (ToolNode → ToolMessage)
        │                            └── back to ON_TURN_START (another round)
        │
        └─ no  ──▶ ON_TURN_END ──▶ ON_AGENT_END ── output_checker (assert the last message is an AIMessage)
                                                        └── latest_to_answer (messages[-1] → final_answer)
                                                        ▼
                                                       END

        │  final_state["final_answer"] (split by split.delimiter + typing delay)
        ▼
main.py  event.reply(group first chunk) / utils.easier_send(api, …)  ──▶  QQ
```
### Directory structure

```
miaoli_bot/
├── main.py                        # plugin entry: MiaoLiBot (builds the container + graph + sub-plugin loader)
├── manifest.toml                  # plugin manifest (name / version / entry_class / pip_dependencies)
├── config.example.yaml            # config template (the real config.yaml is gitignored, it holds secrets)
├── __init__.py                    # root only re-exports the api / models entry points
├── adapters/                      # adapters
│   └── check_pointers/            #   checkpointer adapters: InMemory / SQLite / Postgresql
├── api/                           # the only entry point for sub-plugins (facade, never exposes SHARE_STORE)
│   ├── account_ops.py             #   get_admin_id / get_bot_id / get_admin_nickname / get_bot_nickname
│   ├── platform_ops.py            #   get_ncatbot_api (host runtime handle)
│   ├── store_ops.py               #   store_recall / store_drop / store_update / store_set / store_contains
│   ├── registry_ops.py            #   get_handler_registry / get_tool_registry (the two registry handles)
│   └── sugar.py                   #   get_model_info / get_provider_info / get_prompt (derived from root config)
├── consts/                        # centralised constants
│   ├── graph_events.py            #   the 11 graph events (ON_AGENT_START / ON_TURN_START / ON_BEFORE_COMPACT / ON_COMPACT / ON_AFTER_COMPACT / …)
│   ├── node_priorities.py         #   nine priority tiers (MAXIMUM 9999 … NORMAL 0 … MINIMUM -9999)
│   ├── id_prefix.py               #   session key prefixes (group- / private-)
│   └── share_store_keys.py        #   SHARE_STORE keys (including TOOL_REGISTRY / HANDLER_REGISTRY)
├── core/                          # sub-plugin loading and registration facade (the graph itself moved to miaoli_pipeline)
│   ├── plugin/                    #   sub-plugin loading framework
│   │   ├── loader.py              #   Loader: prepare_plugins / load_plugins / unload_plugins
│   │   ├── plugin.py              #   Plugin: from_path / load / activate / deactivate / unload
│   │   ├── models/                #   PluginMetadata / Dependence / Specifier
│   │   └── errors/                #   BasePluginError / NotAPackageError / MetadataMissingError / EntryClassNotFound
│   └── registries/                #   the two registries
│       ├── handler_registry.py    #   HandlerRegistry: event → graph node registration (on / on_xxx + priority)
│       └── tool_registry.py       #   ToolRegistry: tools by name (register / remove / tools)
├── data/prompts/                  # prompt assets (prompt_v1.0.md ~ prompt_v1.7.md)
├── errors/                        # exception definitions (AgentAborted moved to miaoli_pipeline.errors)
│   ├── base_bot_error.py          #   BaseBotError base class
│   ├── pipeline_stop_dispatch.py  #   PipelineStopDispatch (no remaining consumer, pending removal)
│   └── session_manager_closing_error.py # SessionManagerClosingError
├── models/                        # data models
│   ├── config/                    #   PluginConfig / Provider / LLM / Account / SplitConfig / TypingConfig / SubPluginConfig / CheckPointerConfig
│   ├── graph_state.py             #   GraphState (messages and prompts are checkpointed; the other 6 keys are UntrackedValue)
│   └── graph_runtime_context.py   #   GraphRuntimeContext (not checkpointed: client / tools)
├── plugins/                       # built-in sub-plugins (committed; the load directory is set by sub_plugin.load_from)
│   ├── account_injector/          #   account injection node (nodes/ + metadata.toml)
│   ├── base_nodes/                #   graph nodes (nodes/ + metadata.toml)
│   ├── base_system_tools/         #   system tools (tools/ + models/ + consts/ + config.example.yaml + README)
│   ├── base_topology/             #   default routing (one file per event under nodes/ + config.example.yaml)
│   ├── context_compactor/         #   context compaction (should_compact guard + compact; nodes/ + utils/ + models/ + consts/ + data/ prompt + config.example.yaml + README)
│   ├── intent_recognition/        #   intent recognition: rules match the last message, hits append the configured prompt file as the intent_recognition section (models/ + models/rules/ + protocols/ + nodes/ + utils/ + consts/ + config.example.yaml + README)
│   ├── mcp_adapter/               #   MCP adapter: attach external MCP servers and merge their tools (models/transports + nodes/ + config.example.yaml + README)
│   ├── meme_ops/                  #   meme tools + usage hint injection (tools/ + nodes/ + core/ + models/ + consts/ + config.example.yaml + README)
│   ├── miaoli_bot_adapter/        #   internal data adapter: root config → state and prompts (inject_model_info / inject_soul; nodes/ + models/ + consts/ + config.example.yaml + README)
│   ├── ob11_adapter/              #   OB11 event adapter: two-level parsers + event_adapter (parsers/ + chains/ + api/ + nodes/ + models/ + consts/ + config.example.yaml + README)
│   ├── orphan_tool_fixer/         #   orphan tool-output repair (nodes/ + utils/ + config.example.yaml)
│   ├── pending_tool_fixer/        #   dangling tool-call repair (nodes/ + utils/ + models/ + consts/ + config.example.yaml)
│   ├── prompt_builder/            #   prompt assembly: prompts sections → SystemMessage at messages[0] (nodes/ + README)
│   ├── qq_platform_tools/         #   QQ platform tools (tools/ + README)
│   ├── tool_attachment_fixer/     #   tool attachment repair (nodes/ + utils/ + models/ + consts/ + config.example.yaml + README)
│   ├── tool_permission_manager/   #   tool permission control (nodes/ + models/ + consts/ + config.example.yaml permission table + README)
│   └── web_search/                #   web search (tools/ + models/ + consts/ + config.example.yaml + README)
├── protocols/                     # abstract protocols
│   └── abc/                       #   compile-time abstractions: PluginProtocol / ChainProtocol / StoreProtocol / BaseCheckpointerSaverAdapter
├── stores/                        # global shared store (SHARE_STORE)
├── tests/                         # local pytest cases (gitignored, not committed; pending rewrite)
└── utils/                         # helpers
    ├── easier_sender.py           #   convenience wrappers for private / group sends
    └── sugar.py                   #   concatenate_id (session key group- / private- prefix)
```

## Data flow

1. A QQ message travels NapCat → ncatbot → plugins in registration-priority order. This plugin registers `on_message` at `priority=-100` (post-processing position), so an upstream plugin that stops propagation (e.g. `miaoli_like`'s `赞我` at `priority=100`) prevents it from being seen at all; group messages must also @ `plugin_cfg.account.bot_id`.
2. `on_message` computes `is_group` / `chat_id` / `session_id`, then passes `event._data.model_dump()` as `input["event"]` into the graph; parsing happens inside the graph in `ob11_adapter`'s `event_adapter` (through `EventParseChain` / `SegmentParseChain`).
3. `session_id = concatenate_id(target_id, is_group=is_group)` (groups → `group-<group_id>`, private → `private-<user_id>`), used as the LangGraph `thread_id` — one conversation shares one checkpoint in the saver selected by `checkpointer.database` (memory / sqlite / postgresql), so memory never leaks across conversations.
4. `graph_pipeline.ainvoke({"event": event._data.model_dump()}, thread_id=session_id, context={"client": None, "tools": tool_registry.tools})` — the input carries only `event`; the four model-related values are read from the root config inside the graph by `inject_model_info`.
5. `ON_AGENT_START`'s `event_adapter` (in `ob11_adapter`, `priority=HIGH`) hands `state["event"]` to the parse chain → `event_data`, writes it back into `state["event"]` (so `pick_tools` can read `sender.user_id`), serializes it to JSON and **appends** it to `messages` as a `HumanMessage`. The same event's `inject_account` (in `account_injector`) writes the account info block into the `account_info` section of `prompts` (**`SectionPatch` channel: per-key patches, each plugin owns its section, no overwrites**). `ON_TURN_START` first runs `inject_model_info` (in `miaoli_bot_adapter`, `priority=NORMAL+1`) copying `base_url` / `api_key` / `model` / `max_tokens` into state (also `UntrackedValue`, never persisted), then `build_client` (`priority=NORMAL`) builds a `ChatOpenAI` from those values into `runtime.context["client"]` — the priority guarantees `inject_model_info` runs first.
6. After `ON_TURN_START` comes the **three compaction events**: `ON_BEFORE_COMPACT`'s guard `should_compact` (in `context_compactor`, `priority=NORMAL`) estimates tokens — no compaction → `Goto(ON_BEFORE_REQUEST)`, straight on; compaction needed → `Goto(ON_COMPACT)`, where `compact` squeezes history into one `<abstract>` summary and returns `{"messages": Overwrite([summary, *kept_window])}` to replace history wholesale (`Overwrite` is langgraph's official "write past the reducer" wrapper: `merge_into_updates` keeps it while folding handler outputs, `merge_into_state` consumes it when building the view, so "replace everything" composes in any order with other handlers' "append / targeted delete"). `ON_AFTER_COMPACT`'s default jump goes **back to `ON_TURN_START`** for another round — this time the guard sees the `<abstract>` marker in `messages` and `Abort`s, ending the turn (`AgentAborted` surfaces at the `ainvoke` call site and `main.py` turns it into a notice reply). The `ON_BEFORE_REQUEST` batch (descending priority) first runs `build_prompt` (`priority=NORMAL+1`, in `prompt_builder`) joining `prompts` sections into `<key>value</key>` and placing it at `messages[0]` via `Overwrite`, then `pick_tools` (`priority=1`) which drops tools the sender may not use according to the `config.yaml` permission table and `event.sender.user_id` (undeclared tools are denied with a warning); next `ON_REQUEST` first runs `pending_tool_fixer` (`priority=NORMAL+2`) synthesizing results for dangling `tool_calls` and `orphan_tool_fixer` (`priority=NORMAL+2`) deleting `ToolMessage`s without a matching request (both only produce output when a previous round was interrupted; on valid history they return `None` and write nothing), and finally `call_llm` hands `state["messages"]` (its first item already the `SystemMessage` from `build_prompt`) to the model, appending the returned `AIMessage` to `messages`.
7. `ON_AFTER_REQUEST` is branched by `base_topology`'s `on_after_request` node (registered at the lowest priority `MINIMUM`, so any plugin can preempt it): last message has `tool_calls` → jump to `ON_TOOL_CALLING`, where `invoke_tools` runs the tools via `ToolNode` and appends `ToolMessage`s; if a tool result is **non-string** content (a list of multimodal blocks), the `tool_attachment_fixer` sub-plugin moves it entirely into a `HumanMessage` (the original `ToolMessage` body becomes `replace_text`, only for declared models). Then jump back to `ON_TURN_START` for another round (re-running `build_client` / `pick_tools` / `call_llm`). No `tool_calls` → jump to `ON_TURN_END`, then via `on_turn_end` to `ON_AGENT_END`, where `on_agent_end` returns `Goto(END)` to finish (`END` is filtered by langgraph, so there is no next hop).
8. `ON_AGENT_END`'s `latest_to_answer` reads `messages[-1]`: an `AIMessage`'s `content` becomes `final_answer`; otherwise it falls back to a notice carrying the `thread_id`.
9. `on_message` takes `final_answer` from `final_state` (with `.get()`, since that key is `UntrackedValue` and absent when the turn never reached `on_agent_end`), splits it per root config `split` (`enable` / `delimiter`), skipping empty chunks; when `typing.enable` is on, each chunk sleeps `len(chunk) * uniform(base_speed ± speed_offset)`; in group chats the first chunk goes out via `event.reply` (quoted), while the rest — and every chunk in private chats — go via `utils.easier_send`.
10. Plugin unload (`on_close`): first `await plugin_loader.unload_plugins()` to unload sub-plugins in reverse order (each `deactivate()` forwards `on_close()` then `unload()` clears `sys.modules`; failures stay in the list and can be retried) — **this must happen before clearing shared containers**, because sub-plugins' `on_close` needs `HandlerRegistry` / `ToolRegistry` to detach their nodes and tools; then `await self.cpa.close()` to close the checkpointer explicitly (sqlite closes `aiosqlite` connections, postgresql closes the pool, memory is a no-op); finally the known keys are dropped explicitly (including `TOOL_REGISTRY` / `EVENT_PARSER` / `SEGMENT_PARSER` / `GRAPH_PIPELINE`), and leftovers only produce a warning.

## Built-in sub-plugins

The main package keeps only the checkpointer adapter layer, the `HandlerRegistry` / `ToolRegistry` registries, and the `core.Loader` sub-plugin framework (the graph itself lives in the standalone `miaoli_pipeline` package); all business capability comes from sub-plugins. The seventeen built-in sub-plugins below live in this repo's `plugins/` directory; their `metadata.toml` and `config.example.yaml` templates are committed, while every deployment's real `config.yaml` is gitignored (root one included) and must be copied from the template before editing:

| Sub-plugin | Provides |
|---|---|
| `account_injector` | Account injection: at `on_agent_start`, `inject_account` merges admin/bot QQ numbers and nicknames into the `account_info` section of `prompts` |
| `base_nodes` | Graph nodes: `build_client` / `call_llm` / `invoke_tools` / `latest_to_answer` / `output_checker` (`on_agent_end` asserts the last message is an `AIMessage`) |
| `base_system_tools` | System tools: `bash` / `read_file` / `write` / `replace` / `read_image` (ships `config.yaml` and `README.md`). `read_image` filters formats by the `support_image` list — that filter exists **to restrict reading** (without it, anything read is base64-encoded into an image block in context and the request fails with 400), **not** to classify images for the model |
| `base_topology` | Default routing (the source of order in an edgeless topology): **one node file per event**, 11 nodes each returning one `Goto`, restoring the old `wire()` static edges and `tools_condition` branch at plugin level; `on_after_request` splits the tool loop from wrap-up via `is_tool_calling(messages)`; the three compaction events are also covered here (`on_before_compact` skips compaction → `ON_BEFORE_REQUEST`, `on_after_compact` jumps back to `ON_TURN_START`). Registers at the lowest priority `MINIMUM`, so any sub-plugin can preempt it |
| `context_compactor` | Context compaction split into **guard + compaction**: `should_compact` on `on_before_compact` (`priority=NORMAL`) reads the model's real `context_window` / `max_tokens` and returns `Goto(ON_COMPACT)` or `Goto(ON_BEFORE_REQUEST)`; `compact` on `on_compact` squeezes history into one `<abstract>` summary and replaces it with `Overwrite`. Keep-count / prompt / whether to restore the system prompt / counting mode are all configurable (`base` rough estimate or `tiktoken` exact); ships `plugins/context_compactor/data/compact_prompt.md` and `README.md` |
| `intent_recognition` | Intent recognition: `recognize_intent` on `on_before_request` (`priority=NORMAL+2`, which must run before `prompt_builder`'s `NORMAL+1` — larger value first) matches the last message's text against configured `matchers`. Multiple rules inside one matcher are an **AND** relation (`all()`); on a hit, `file` is read with `encoding` and keyed by `name`; all hits are merged into **one** `intent_recognition` section (`name` is only a sub-label inside it). Four matching modes form a discriminated union keyed by `mode`: `single_keyword` (substring) / `any_keywords` (any hit) / `min_keywords` (at least `count` hits) / `regex` (`re.search`). Text is extracted from multimodal content by `get_content`, keeping only dict blocks with a `str` `text` key plus bare string blocks; image / `tool_use` blocks are skipped (so base64 data URLs never enter matching). A failing matcher only invalidates itself and logs `ERROR`; `enable` defaults to `false`. Ships `README.md` |
| `mcp_adapter` | MCP adapter: `recall_mcp_tools` on `on_before_request` (`priority=MEDIUM`) pulls tools from external MCP servers with `MultiServerMCPClient` and merges them into `runtime.context["tools"]` after **deduplicating by name**; it must run before `pick_tools` (`priority=1`), otherwise MCP tools bypass the permission filter. Supports `stdio` / `streamable_http` transports, with an optional per-server `reusable` flag (stable tool lists are cached after the first fetch, managed by `MCPClientRegistry`). Ships `README.md`. **Incomplete**: dedupe only, no removal |
| `meme_ops` | Meme tools: archive / send / delete-by-hash; `inject_doc` on `on_agent_start` (`priority=NORMAL`) writes `plugins/meme_ops/data/meme_helper.md` into the `meme_helper` section, while `inject_memes` at the same event writes the archived memes as a `hash: description: tags` list into the `available_memes` section, so the model never needs a tool call to enumerate them; `inject_doc` states the four criteria for archiving; with `enable: false` neither tools nor nodes register. Ships `README.md` documenting the privacy risk that the model may archive ordinary user images as memes |
| `miaoli_bot_adapter` | Internal data adapter: both nodes sit on `on_turn_start` (`priority=NORMAL+1`). `inject_model_info` calls `miaoli_bot.api`'s `get_provider_info` / `get_model_info` to write `base_url` / `api_key` / `model` / `max_tokens` into state for `build_client`; `inject_soul` writes the persona file named by `prompt_file` into the `soul` section for `prompt_builder`. Graph nodes therefore never need to know whether the root config's `providers` is a list or a dict. Must run before `build_client` (`NORMAL`). Ships `README.md` |
| `orphan_tool_fixer` | Broken-history repair: `fix_orphan_tool_message` on `on_request` (`priority=NORMAL+2`) deletes `ToolMessage`s with no originating `tool_calls` (emits only targeted deletions) |
| `pending_tool_fixer` | Broken-history repair: `fix_pending_tool_call` on `on_request` (`priority=NORMAL+2`) adds a synthesized "tool was not executed" `ToolMessage` for dangling `tool_calls` (returns a full-table `Overwrite`) |
| `ob11_adapter` | OB11 event adapter (**pure adapter, parse only, never sends**): `event_adapter` on `on_agent_start` (`priority=HIGH`) parses the ncatbot event dict into `event_data`, writes it back into `state["event"]`, and appends the JSON to `messages`; the two-level parse chain (`parsers/`) works on plain dicts and imports no ncatbot class. Sending is `main.py`'s job. Ships `config.yaml` and `README.md` |
| `prompt_builder` | Prompt assembly: `build_prompt` on `on_before_request` (`priority=NORMAL+1`) joins the `prompts` sections into `<key>value</key>` and puts the result at `messages[0]` with `Overwrite`; when it matches the existing first `SystemMessage` it returns `None` and writes nothing. Ships `README.md` |
| `qq_platform_tools` | QQ platform tools: send message / send file / download file / query message id / recall message / poke (`send_poke`: with `group_id` it pokes in the group, without it pokes in private chat). Ships `README.md` |
| `tool_attachment_fixer` | Tool attachment repair: `fix_tool_attachment` on `on_tool_call` (`priority=-2`) moves non-string `ToolMessage.content` into a following `HumanMessage` (the original body becomes `replace_text`), so models that reject multimodal blocks inside `tool` messages stop returning 400; only applies to models declared in `models` (empty = all), returns `None` when nothing changes. Ships `README.md` |
| `tool_permission_manager` | Tool permission control: using the `config.yaml` permission table (`admin` / `white_list` / `anyone` / `passerby` / `nobody`), on `on_before_request` (`priority=1`) it removes tools the current identity may not use from `runtime.context["tools"]`; undeclared tools are denied with a warning (`debug: false` silences the log, not the decision). Ships `README.md` |
| `web_search` | Web search: registers one `web_search` tool (**the tool name is backend-independent**); `adapter` selects the backend — `langsearch` (`POST /v1/web-search`) or `deepseek` (`POST /v1/tools/search`), and the raw response goes to the model as-is. `adapter` only affects the input schema and the response shape, never the tool name. Ships `README.md` |

> `orphan_tool_fixer` and `pending_tool_fixer` are a pair: the former treats "a result without a request", the latter "a request without a result". They are independent and order-insensitive (`accumulate_data` lets differently shaped deltas fold in any order); they are triggered when an earlier round's tool execution was interrupted or collided, after which every request fails with `400 insufficient tool messages following tool_calls`.

Sub-plugin conventions: each directory holds a `metadata.toml` (`name` / `entry_class` / `description` / `dependences`; `entry_class` is a dotted path such as `main.IntentRecognition`, or just the class name when the entry class lives in `__init__.py`) plus a committed `config.example.yaml` template (the real `config.yaml` is never committed). **A `config.yaml` must exist at runtime**: when it is missing the framework does not supply `{}` — `self.config` is `None` (`PluginConfig.model_validate(None)` raises `ValidationError`, and the plugin is marked failed during activation). The entry class implements `PluginProtocol`, attaches graph nodes with `HandlerRegistry` and registers tools with `ToolRegistry` in `on_load` (parsers are managed by `ob11_adapter`'s own `ParserRegistry`), then detaches them in `on_close` with `HandlerRegistry.remove_*()` / `ToolRegistry.remove()` before releasing other resources.

## Installation and usage

1. **Move this directory into the `plugins/` directory created by ncatbot** (e.g. `/root/Ncatbot_QQ/plugins/miaoli_bot`). This is an ncatbot plugin, not a Python package, so **it is not installed with pip** — ncatbot scans `plugins/` on startup and loads any directory containing `manifest.toml`.
2. Make sure the runtime dependencies are installed (`manifest.toml`'s `pip_dependencies` are installed automatically when `plugin.auto_install_pip_deps` is enabled):
   - `ncatbot5` (`>=5.5.8`, import name `ncatbot`)
   - `langgraph` (`>=1.2.12`)
   - `langchain-core` (`>=1.6.5`): `@tool` definitions / `BaseMessage` / `BaseChatModel` and other base types
   - `langchain-openai` (`>=1.6.6`)
   - `langgraph-checkpoint-sqlite` (`>=3.1.1`, used when `database: sqlite`)
   - `langgraph-checkpoint-postgres` (`>=3.1.2`, used when `database: postgresql`)
   - `aiosqlite` (`>=0.22.1`) / `psycopg` (`>=3.3.6`) / `psycopg-pool` (`>=3.3.3`): drivers and pools imported directly (`SQLiteAdapter` / `PostgresqlAdapter` / `MemeSqlite`)
   - `aiofiles` (`>=24.1.0`): async writes for `base_system_tools`' `write` / `replace`
   - `aiohttp` (`>=3.13.4`): HTTP client for `web_search` (`ClientSession`)
   - `pydantic` (`>=2.13.5`): config models (`models/config/`) and tool argument schemas
   - `pyyaml` (`>=6.0.3`): sub-plugin `config.yaml` parsing (`yaml.safe_load` in `core/plugin/plugin.py`)
   - `filetype` (`>=1.2.0`)
   - `pillow` (`>=12.3.0`)
   - `tiktoken` (`>=0.14.0`)
   - `langchain-mcp-adapters` (`>=0.3.2`): `mcp_adapter`'s `MultiServerMCPClient` (`langchain_mcp_adapters.client`)
   - `mcp` (`>=1.24.0`): the MCP protocol SDK, pulled in by the adapter above and declared explicitly here
   - **`miaoli_pipeline` is not on that list**: `pip_dependencies` only accepts "package name + PEP 440 constraint", and this package is not on PyPI, so it cannot be installed that way. It is a normal Python package and must be installed once from its **local repository directory** — see the note in [Dependencies](#dependencies) below.
3. Configure the plugin: `cp config.example.yaml config.yaml` and fill in a real `api_key` (`config.yaml` holds secrets and is gitignored). The plugin directory's `config.yaml` provides defaults, and the global `config.yaml`'s `plugin.plugin_configs.miaoli_bot` overrides matching keys; `on_load` starts with `PluginConfig.model_validate(self.config)`, so missing required fields / nonexistent paths / wrong types raise `ValidationError`, the plugin fails to load with a traceback in the log (the rest of the bot is unaffected).

Configuration keys map one-to-one onto the fields of `models.PluginConfig`:

| Key | Default / required | Purpose |
|---|---|---|
| `provider` / `model` | **required** | Which provider and which model to use — two names that `model_validator` checks against `providers` |
| `providers` | **required** | `List[Provider]`, at least one entry; each is identified by its `name` field |
| `providers[].name` | **required** | Provider name (the value of `provider`) |
| `providers[].base_url` | **required** | Request URL (**no path is appended**, so fill it up to the `/v1` level) |
| `providers[].api_key` | **required** | Auth key |
| `providers[].protocol` | **required** | `openai-completions` / `openai-responses` |
| `providers[].models` | **required** | `List[LLM]`, at least one entry; each is identified by its `name` field |
| `providers[].models[].name` | **required** | Model name (the value of `model`) |
| `providers[].models[].context_window` | `128000` | Context window |
| `providers[].models[].max_tokens` | `4096` | Maximum output tokens |
| `providers[].models[].support_visions` | **required** | Modalities the model accepts, at least one of `image` / `video` / `text` / `audio` |
| `account` | **required** | `bot_id` / `admin_id` / `bot_nickname` / `admin_nickname`, all four required; `account_injector`'s `inject_account` builds the prompt block from them, and `admin_id` is also what the permission plugin uses to recognise the admin |
| `prompt_file` | `null` | Path to the system prompt file; the `prompt` property lazy-loads it as UTF-8 on first access |
| `split` | `SplitConfig()` | `enable` (default `true`) / `delimiter` (default `null`, the reply split delimiter) — `delimiter` must be non-empty when `enable` is true, otherwise validation fails; `on_message` splits replies with it |
| `typing` | `TypingConfig()` | `enable` (default `true`) / `base_speed` (default `0`, seconds per character) / `speed_offset` (default `0`, random jitter) — `on_message` sleeps `len(chunk) * uniform(base_speed ± speed_offset)` |
| `checkpointer` | `CheckPointerConfig()` | `database` (`memory` / `sqlite` / `postgresql`, default `memory`) / `connect_to` (database URL, **required unless `memory`**) / `extra` (extra kwargs passed straight to the adapter's `connect(**kwargs)`; postgresql understands `max_size` default 8 / `min_size` default 4 / `autocommit` default `true` / `row_factory` default `dict_row`) — `on_load` picks the adapter from `CPA_MAPPING` by `database` and connects (wired up since 0.9.0), `on_close` calls `close()` |
| `sub_plugin` | `SubPluginConfig()` | `enable` (default `false`, **currently unused**) / `load_from` (`List[Path]`, empty by default); `core.Loader` runs `prepare_plugins()` (read `metadata.toml`, skip non-packages) → `load_plugins()` (load in topological order) → `unload_plugins()` |

4. Start the bot and talk to it in a QQ private chat or a group (groups need an @ mention).

### Local tests

```bash
cd <parent of the plugin>   # plugins/
<venv>/bin/python -m pytest miaoli_bot/tests/ -v
```

> Note: the cases in `tests/` still target the old pi bridge layer and were invalidated by the 0.8.0 refactor; they await a rewrite.

## Dependencies

| Package | Purpose |
|---|---|
| `ncatbot5` (`>=5.5.8`, import name `ncatbot`) | QQ bot framework / event and message APIs |
| `langgraph` (`>=1.2.12`) | Graph pipeline (`StateGraph` / `Command` / `Overwrite` / `ToolNode` / checkpoints) |
| [`miaoli_pipeline`](https://github.com/lyt2011/miaoli_pipeline) (`>=1.1.0`) | The event pipeline itself: `GraphPipeline` (`register_handler` / `unregister_handler` / `wire` / `compile` / `ainvoke` / priority orchestration), `BaseNodeAction` (`Continue` / `Goto` / `Abort`), the `SectionPatch` channel. **Not published on PyPI**, so it can only be installed from its local repository directory — see the note below |
| `langchain-openai` (`>=1.6.6`) | `ChatOpenAI` (any OpenAI-compatible endpoint) |
| `langchain-core` (`>=1.6.5`) | `@tool` definitions, `BaseMessage` / `BaseChatModel` and other base types (used by the main package and sub-plugins alike) |
| `langgraph-checkpoint-sqlite` (`>=3.1.1`) | `AsyncSqliteSaver` (`checkpointer.database: sqlite`), bringing `aiosqlite` / `sqlite-vec` |
| `langgraph-checkpoint-postgres` (`>=3.1.2`) | `AsyncPostgresSaver` (`checkpointer.database: postgresql`), bringing `psycopg` / `psycopg-pool` |
| `aiosqlite` (`>=0.22.1`) | Async sqlite driver shared by `SQLiteAdapter` and `meme_ops.MemeSqlite` (connections closed by `close()` / `__aexit__`) |
| `aiofiles` (`>=24.1.0`) | Async disk writes for `base_system_tools`' `write` / `replace` (`aiofiles.open` + `async with`) |
| `aiohttp` (`>=3.13.4`) | Web search requests in `web_search` (`ClientSession.post`); also a transitive dependency of `ncatbot5`, declared explicitly here |
| `psycopg` (`>=3.3.6`) / `psycopg-pool` (`>=3.3.3`) | Driver and pool imported directly by `PostgresqlAdapter` (`AsyncConnectionPool`) |
| `pydantic` (`>=2.13.5`) | Config models (`BaseModel` / `Field` / `model_validator`) and tool argument schemas |
| `pyyaml` (`>=6.0.3`) | `yaml.safe_load` for sub-plugin `config.yaml` in `core/plugin/plugin.py` |
| `filetype` (`>=1.2.0`) | Image type sniffing in `base_system_tools` (`read_image`) |
| `pillow` (`>=12.3.0`) | Image dimension parsing in `context_compactor` (`image_to_tokens`, used to estimate image tokens) |
| `tiktoken` (`>=0.14.0`) | Exact token counting in `context_compactor` (`calculate.mode: tiktoken`) |
| `langchain-mcp-adapters` (`>=0.3.2`) | `mcp_adapter`'s `MultiServerMCPClient` (fetch / call tools of external MCP servers) |
| `mcp` (`>=1.24.0`) | MCP protocol SDK (pulled in by `langchain-mcp-adapters`, declared explicitly so an upstream dependency change cannot cause an import-time `ModuleNotFoundError`) |

> Note: the dependencies above are declared in `manifest.toml`'s `pip_dependencies` — but **`miaoli_pipeline` is not among them**: `pip_dependencies` only accepts "package name + PEP 440 constraint", and `miaoli_pipeline` **is not published on PyPI**, so a bare package name cannot be installed and a git URL makes auto-install fail. It is an ordinary installable Python package and only needs to be installed once from its **local repository directory**:
>
> ```bash
> pip install /path/to/miaoli_pipeline
> ```
>
> Afterwards `import miaoli_pipeline` works; its only dependency is `langgraph>=1.2,<2` (already declared above).
> Note: versions 0.7.0 and earlier depended on `pi_bridge` and an external pi agent process; both were removed in 0.8.0.

## Project status

This section only describes **what the project is now**; it does not accumulate per release — see [`CHANGELOG.md`](../CHANGELOG.md) for what changed in each version.

**Current shape**

- The main package does only three things: the checkpointer adapter layer, the `HandlerRegistry` / `ToolRegistry` registries, and the `core.Loader` sub-plugin framework. The graph itself has moved to the standalone [`miaoli_pipeline`](https://github.com/lyt2011/miaoli_pipeline) package; it is not on PyPI, so deployments install it from GitHub
- All business logic comes from the **17** sub-plugins (see [Built-in sub-plugins](#built-in-sub-plugins)). Each ships its own `README.md` and a committed `config.example.yaml`; real `config.yaml` files are always gitignored and copied from the templates at deploy time
- The end-to-end path has been running on a real server for a long time: real QQ message → OB11 event dict → graph pipeline → LLM → tool loop → reply
- Context compaction, tool permissions, MCP integration, web search, memes, and intent recognition are all wired in, each with an independent `enable` switch

**Known limitations**

- **Tools expose "who may use them", not "what they may do"**: the process runs as root and `tool_permission_manager` only controls tool visibility; once `bash` / `write` / `replace` are allowed there is no filesystem boundary
- **`mcp_adapter` dedupes but never withdraws**: tools removed by an MCP server never disappear from the tool table
- **Compact summaries are "summaries of summaries"**: the second compaction consumes the first one's output, so details inevitably erode as compaction repeats — the longer the conversation, the more visible
- **`intent_recognition` is pure string matching**: no semantic understanding, and the criterion only sees the last message's text. Conditions that need context or tool results ("did I send the previous one", "does this image count as a meme") do not fit the current `is_hit(data)` signature
