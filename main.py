from ncatbot.plugin		import NcatBotPlugin
from ncatbot.core		import registrar
from ncatbot.event.qq	import MessageEvent

from pathlib	import Path
from typing		import List, Optional

from langgraph.checkpoint.memory	import InMemorySaver
from langchain_core.tools			import BaseTool
from langchain_openai				import ChatOpenAI

from .core		import (
	GraphPipeline,
	call_llm,
	format_input,
	format_prompt,
	last_msg_to_answer,
	on_tool_calling,
)
from .chains	import EventParseChain, SegmentParseChain
from .stores	import SHARE_STORE
from .adapters	import EventAdapter
from .protocols	import Closable
from .models	import GraphRuntimeContext, GraphState, PluginConfig
from .parsers	import (
	GroupMessageEventParser,
	PrivateMessageEventParser,
	AtSegmentParser,
	TextSegmentParser,
	ImageSegmentParser,
	FileSegmentParser,
	ReplySegmentParser,
)
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
	PLUGIN_DIR as c_PLUGIN_DIR,
	GRAPH_PIPELINE,
	ON_REQUEST,
	ON_TURN_END,
	ON_TURN_START,
	WORKSPACE_DIR,
	ON_TOOL_CALLING,
)
from .tools	import (
	send_message_to_qq,
	send_meme_to_qq,
	send_file_to_qq,
	list_memes,
	archive_meme,
	download_qq_file,
	query_qq_message_id,
	delete_qq_message,
)

import asyncio


PLUGIN_NAME	= "喵璃の本体"
PLUGIN_DIR	= Path(__file__).resolve().parent

TOOLS: List[BaseTool] = [
	send_message_to_qq,
	send_meme_to_qq,
	send_file_to_qq,
	list_memes,
	archive_meme,
	download_qq_file,
	query_qq_message_id,
	delete_qq_message,
]


class MiaoLiBot(NcatBotPlugin):
	
	def __init__(self, *args, **kwargs) -> None:
		
		super().__init__(*args, **kwargs)
		
		self.store_lock	= asyncio.Lock()
		
		self.cfg: Optional[PluginConfig] = None
	
	async def _build_graph(self) -> None:
		
		if SHARE_STORE.contains(GRAPH_PIPELINE):
			return None
		
		graph_pipeline = GraphPipeline(GraphState, context_schema=GraphRuntimeContext)
		
		graph_pipeline.register(ON_TURN_START, format_input)
		graph_pipeline.register(ON_TURN_START, format_prompt)
		graph_pipeline.register(ON_REQUEST, call_llm)
		graph_pipeline.register(ON_TURN_END, last_msg_to_answer)
		graph_pipeline.register(ON_TOOL_CALLING, on_tool_calling)
		
		graph_pipeline.wire()
		graph_pipeline.compile(checkpointer=InMemorySaver())
		
		# double-check 防止塞垃圾/替换原有对象
		if not SHARE_STORE.contains(GRAPH_PIPELINE):
			SHARE_STORE.set(GRAPH_PIPELINE, graph_pipeline)
	
	async def _register_event_parse_chain(self) -> None:
		
		"""event 解析链已注册后不会重新注册"""
		
		async with self.store_lock:
		
			if SHARE_STORE.contains(EVENT_PARSER):
				return None
			
			parse_chain = EventParseChain()
			SHARE_STORE.set(EVENT_PARSER, parse_chain)
		
		parse_chain.register_parser(GroupMessageEventParser())
		parse_chain.register_parser(PrivateMessageEventParser())
	
	async def _register_segment_parse_chain(self) -> None:
		
		"""segment 解析链已注册后不会重新注册"""
		
		async with self.store_lock:
		
			if SHARE_STORE.contains(SEGMENT_PARSER):
				return None
			
			parse_chain = SegmentParseChain()
			SHARE_STORE.set(SEGMENT_PARSER, parse_chain)
		
		parse_chain.register_parser(TextSegmentParser())
		parse_chain.register_parser(AtSegmentParser())
		parse_chain.register_parser(ImageSegmentParser())
		parse_chain.register_parser(FileSegmentParser())
		parse_chain.register_parser(ReplySegmentParser())
	
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
	
		self.cfg = PluginConfig.model_validate(self.config)
		
		SHARE_STORE.set(NCATBOT_API, self.api)
		SHARE_STORE.set(PLUGIN_CONFIG, self.cfg)
		SHARE_STORE.set(RAW_CONFIG, self.config)
		SHARE_STORE.set(c_PLUGIN_DIR, PLUGIN_DIR)
		SHARE_STORE.set(WORKSPACE_DIR, self.workspace)
		
		await self._build_graph()
		await self._register_event_parse_chain()
		await self._register_segment_parse_chain()
		
		self.logger.info(f"{PLUGIN_NAME} 已加载")
		
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(NCATBOT_API)
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
		SHARE_STORE.drop(c_PLUGIN_DIR)
		SHARE_STORE.drop(GRAPH_PIPELINE)
		SHARE_STORE.drop(WORKSPACE_DIR)
		
		# **兜底清理不代表可以不清理**
		await self.clean_share_store()
				
		if not SHARE_STORE.is_empty():
			self.logger.warning(f"共享容器可能存在资源泄露: {list(SHARE_STORE.keys())}")
		
		self.logger.info(f"{PLUGIN_NAME} 已卸载")
	
	@registrar.on_message(priority=-100)
	async def on_message(self, event: MessageEvent) -> None:
		
		is_group		= event.is_group_msg()
		target_id		= get_id_from_event(event)
		event_adapter	= EventAdapter.build(event)
		session_id		= concatenate_id(target_id, is_group=is_group)
		
		if is_group and not event.message.is_at("2449906317", all_except=True):
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
		
		graph_pipeline = SHARE_STORE.recall(GRAPH_PIPELINE, None)
		if graph_pipeline is None:
			self.logger.warning("graph_pipeline 未加载 跳过")
			return
		
		# HACK: 快速测试技术债 后续改成动态创建
		chat_model	= ChatOpenAI(model="deepseek-flash", base_url="https://api.deepseek.com/v1", api_key=self.cfg.providers[0].api_key)
		input		= {"event": parse_result.event, "segments": parse_result.segments}
		context		= {"plugin_config": self.cfg, "chat_model": chat_model, "tools": TOOLS}
		
		output = await graph_pipeline.ainvoke(input, thread_id=session_id, context=context)
		
		# TODO: 添加\n\n分割
		# TODO: 添加打字时间延迟
		await event_adapter.send(self.api, output["final_answer"])