from ncatbot.plugin		import NcatBotPlugin
from ncatbot.core		import registrar
from ncatbot.event.qq	import MessageEvent

from pathlib	import Path
from typing		import Optional

from langgraph.checkpoint.memory	import InMemorySaver
from langchain_openai				import ChatOpenAI

from .core		import GraphPipeline, ToolRegistry, PluginLoader, registry
from .chains	import EventParseChain, SegmentParseChain
from .stores	import SHARE_STORE
from .adapters	import EventAdapter
from .protocols	import Closable
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

import asyncio
import random


PLUGIN_NAME	= "喵璃の本体"


class MiaoLiBot(NcatBotPlugin):
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.plugin_loader: Optional[PluginLoader] = None
	
	@staticmethod
	def _build_graph() -> GraphPipeline:
		
		graph_pipeline = GraphPipeline(GraphState, context_schema=GraphRuntimeContext)
		graph_pipeline.wire()
		graph_pipeline.compile(checkpointer=InMemorySaver())
		
		return graph_pipeline
	
	async def clean_share_store(self) -> None:
		
		"""
		基于 Closable 协议清理共享容器
		不能保证全部清理 尽力兜底
		还是建议手动清理已知的

		非 Closable 的键只记 warning 跳过（留在容器里 由显式清理负责）
		close 抛错的键不影响其余键 close 后 double-check 丢弃残留
		"""
		
		share_keys		= list(SHARE_STORE.keys())
		share_values	= list(SHARE_STORE.values())
		
		for key, value in zip(share_keys, share_values):
			
			if not isinstance(value, Closable):
				self.logger.warning(f"{key} 不是 Closable 跳过清理")
				continue
			
			try:
				await value.close()
			
			except Exception as e:
				self.logger.warning(f"{key} 清理时发生错误: {e}")
			
			else:
				
				# double-check 防止卡奇奇怪怪的bug
				if SHARE_STORE.contains(key):
					SHARE_STORE.drop(key)
				
				else:
					self.logger.warning(f"{key} 不存在 但清理完成")
				
				self.logger.info(f"{key} 被兜底逻辑清理")
		
		return
	
	async def on_load(self) -> None:
		
		plugin_config = PluginConfig.model_validate(self.config)
		
		SHARE_STORE.set(NCATBOT_API, self.api)
		
		SHARE_STORE.set(PLUGIN_CONFIG, plugin_config)
		SHARE_STORE.set(RAW_CONFIG, self.config)
		
		SHARE_STORE.set(PLUGIN_DIR, Path(__file__).resolve().parent)
		SHARE_STORE.set(WORKSPACE_DIR, self.workspace)
		
		SHARE_STORE.set(TOOL_REGISTRY, ToolRegistry())
		SHARE_STORE.set(SEGMENT_PARSER, SegmentParseChain())
		SHARE_STORE.set(EVENT_PARSER, EventParseChain())
		SHARE_STORE.set(GRAPH_PIPELINE, self._build_graph())
		
		self.plugin_loader = PluginLoader(
			path		= plugin_config.sub_plugin.load_from,
			config		= plugin_config,
			registry	= registry,
		)
		await self.plugin_loader.load_all()
		
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
		
		await self.clean_share_store()
		await self.plugin_loader.unload_all()
				
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