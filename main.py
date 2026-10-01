from ncatbot.plugin		import NcatBotPlugin
from ncatbot.core		import registrar
from ncatbot.event.qq	import MessageEvent

from pathlib	import Path
from typing		import Optional

from langgraph.checkpoint.memory	import InMemorySaver
from langchain_openai				import ChatOpenAI
from langgraph.checkpoint.base		import BaseCheckpointSaver

from .core		import GraphPipeline, ToolRegistry, PluginLoader, registry
from .chains	import EventParseChain, SegmentParseChain
from .stores	import SHARE_STORE
from .protocols	import BaseCheckpointerSaverAdapter as BCSA
from .models	import GraphRuntimeContext, GraphState, PluginConfig
from .utils		import (
	parse_message,
	get_id_from_event,
	concatenate_id,
)
from .consts	import (
	EVENT_PARSER,
	SEGMENT_PARSER,
	NCATBOT_API,
	PLUGIN_CONFIG,
	RAW_CONFIG,
	PLUGIN_DIR,
	GRAPH_PIPELINE,
	TOOL_REGISTRY,
	WORKSPACE_DIR,
)
from .adapters	import (
	EventAdapter,
	InMemoryAdapter,
	SQLiteAdapter,
	PostgresqlAdapter,
)

import asyncio
import random


PLUGIN_NAME	= "喵璃の本体"
CPA_MAPPING	= {
	"sqlite"	: SQLiteAdapter,
	"postgresql": PostgresqlAdapter,
	"memory"	: InMemoryAdapter,
}


class MiaoLiBot(NcatBotPlugin):
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.plugin_loader	: Optional[PluginLoader]	= None
		self.cpa			: Optional[BCSA]			= None
	
	@staticmethod
	def _build_graph(checkpointer: BaseCheckpointSaver) -> GraphPipeline:
		
		graph_pipeline = GraphPipeline(GraphState, context_schema=GraphRuntimeContext)
		graph_pipeline.wire()
		graph_pipeline.compile(checkpointer=checkpointer)
		
		return graph_pipeline
	
	async def on_load(self) -> None:
		
		plugin_config = PluginConfig.model_validate(self.config)
		
		database	= plugin_config.checkpointer.database
		connect_to	= plugin_config.checkpointer.connect_to
		extra		= plugin_config.checkpointer.extra
		self.cpa	= await CPA_MAPPING[database].connect(connect_to, **extra)
		
		SHARE_STORE.set(NCATBOT_API, self.api)
		
		SHARE_STORE.set(PLUGIN_CONFIG, plugin_config)
		SHARE_STORE.set(RAW_CONFIG, self.config)
		
		SHARE_STORE.set(PLUGIN_DIR, Path(__file__).resolve().parent)
		SHARE_STORE.set(WORKSPACE_DIR, self.workspace)
		
		SHARE_STORE.set(TOOL_REGISTRY, ToolRegistry())
		SHARE_STORE.set(SEGMENT_PARSER, SegmentParseChain())
		SHARE_STORE.set(EVENT_PARSER, EventParseChain())
		SHARE_STORE.set(GRAPH_PIPELINE, self._build_graph(checkpointer=self.cpa))
		
		self.plugin_loader = PluginLoader(
			path		= plugin_config.sub_plugin.load_from,
			config		= plugin_config,
			registry	= registry,
		)
		await self.plugin_loader.load_all() # NOTE: 一个插件错误会全炸完
		
		self.logger.info(f"{PLUGIN_NAME} 已加载")
		
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(NCATBOT_API)
		
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
		
		SHARE_STORE.drop(PLUGIN_DIR)
		SHARE_STORE.drop(WORKSPACE_DIR)
		
		SHARE_STORE.drop(TOOL_REGISTRY)
		SHARE_STORE.drop(SEGMENT_PARSER)
		SHARE_STORE.drop(EVENT_PARSER)
		SHARE_STORE.drop(GRAPH_PIPELINE)
		
		await self.plugin_loader.unload_all()
		await self.cpa.close()
				
		if not SHARE_STORE.is_empty():
			self.logger.warning(f"共享容器可能存在资源泄露: {list(SHARE_STORE.keys())}")
		
		self.logger.info(f"{PLUGIN_NAME} 已卸载")
	
	@registrar.on_message(priority=-100)
	async def on_message(self, event: MessageEvent) -> None:
		
		is_group		= event.is_group_msg()
		target_id		= get_id_from_event(event)
		event_adapter	= EventAdapter.build(event)
		session_id		= concatenate_id(target_id, is_group=is_group)
		
		graph_pipeline	= SHARE_STORE.recall(GRAPH_PIPELINE)
		plugin_cfg		= SHARE_STORE.recall(PLUGIN_CONFIG)
		tool_registry	= SHARE_STORE.recall(TOOL_REGISTRY)
		
		if is_group and not event.message.is_at(plugin_cfg.account.bot_id, all_except=True):
			self.logger.warning("群消息无@ 已跳过")
			return
		
		segment = getattr(event, "message", None)
		if not segment:
			self.logger.warning("segment 无内容或 event 不含 segment")
			return
		
		parse_result = await parse_message(event, segment)
		if parse_result is None:
			self.logger.warning("事件解析失败 跳过")
			return
		
		# HACK: 快速测试技术债 后续改成动态创建 (LLMManager)
		chat_model	= ChatOpenAI(model="deepseek-flash", base_url="https://api.deepseek.com/v1", api_key=plugin_cfg.providers[0].api_key)
		input		= {"event": parse_result.event, "segments": parse_result.segments}
		context		= {"plugin_config": plugin_cfg, "chat_model": chat_model, "tools": tool_registry.tools}
		
		output = await graph_pipeline.ainvoke(input, thread_id=session_id, context=context)
		
		# 修复空 split_separator 导致的 TypeError 问题
		if plugin_cfg.output.split_separator is None:
			final_answer = output["final_answer"]
		
		else:
			final_answer = output["final_answer"].split(plugin_cfg.output.split_separator)
		
		for answer in final_answer:
			
			if not answer:
				continue
			
			total_char_time	= len(answer) * plugin_cfg.output.typing_speed
			max_char_time	= total_char_time + plugin_cfg.output.typing_speed_offset
			mim_char_time	= total_char_time - plugin_cfg.output.typing_speed_offset
			
			await asyncio.sleep(random.uniform(mim_char_time, max_char_time))
			await event_adapter.send(self.api, answer)