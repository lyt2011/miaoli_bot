from ncatbot.plugin		import NcatBotPlugin
from ncatbot.core		import registrar
from ncatbot.event.qq	import MessageEvent
from ncatbot.utils		import get_log

from pi_bridge	import models
from pathlib	import Path

from .chains	import EventParseChain, SegmentParseChain
from .core		import PIToolBackend, PiClient
from .stores	import SHARE_STORE
from .adapters	import EventAdapter
from .parsers	import (
	GroupMessageEventParser,
	PrivateMessageEventParser,
	AtSegmentParser,
	TextSegmentParser,
	ImageSegmentParser,
	FileSegmentParser,
	ReplySegmentParser,
)
from .tools		import (
	send_message_to_QQ,
	download_qq_file,
	query_qq_message_id
)
from .utils		import (
	easier_send,
	parse_message,
	get_id_from_event,
	is_agent_end,
	is_agent_error,
	is_thinking_delta,
	is_text_delta,
)
from .consts	import (
	EVENT_PARSER,
	SEGMENT_PARSER,
	NCATBOT_API,
	TOOL_BACKEND,
	PLUGIN_CONFIG,
)

import json
import asyncio


class MiaoLiBot(NcatBotPlugin):
	
	def __init__(self, *args, **kwargs) -> None:
		
		super().__init__(*args, **kwargs)
		
		self._share_store_lock	= asyncio.Lock()
		self._plugin_lock		= asyncio.Lock()
	
	async def _register_event_parse_chain(self) -> None:
		
		"""event 解析链已注册后不会重新注册"""
		
		async with self._share_store_lock:
		
			if SHARE_STORE.contains(EVENT_PARSER):
				return None
			
			parse_chain = EventParseChain()
			SHARE_STORE.set(EVENT_PARSER, parse_chain)
		
		parse_chain.register_parser(GroupMessageEventParser())
		parse_chain.register_parser(PrivateMessageEventParser())
	
	async def _register_segment_parse_chain(self) -> None:
		
		"""segment 解析链已注册后不会重新注册"""
		
		async with self._share_store_lock:
		
			if SHARE_STORE.contains(SEGMENT_PARSER):
				return None
			
			parse_chain = SegmentParseChain()
			SHARE_STORE.set(SEGMENT_PARSER, parse_chain)
		
		parse_chain.register_parser(TextSegmentParser())
		parse_chain.register_parser(AtSegmentParser())
		parse_chain.register_parser(ImageSegmentParser())
		parse_chain.register_parser(FileSegmentParser())
		parse_chain.register_parser(ReplySegmentParser())
		
	async def _register_tools(self) -> None:
		
		"""统一注册工具"""
		
		async with self._share_store_lock:
		
			if SHARE_STORE.contains(TOOL_BACKEND):
				return None
		
			tool_backend = PIToolBackend()
			SHARE_STORE.set(TOOL_BACKEND, tool_backend)
		
		tool_backend.register_tool(send_message_to_QQ)
		tool_backend.register_tool(download_qq_file)
		tool_backend.register_tool(query_qq_message_id)
		
		await tool_backend.run_server()
	
	async def _close_tool_backend(self) -> None:
		
		async with self._share_store_lock:
			
			tool_backend = SHARE_STORE.recall(TOOL_BACKEND, None)
			
			if tool_backend is not None:
				SHARE_STORE.drop(TOOL_BACKEND)
		
		# double-check并打印日志
		if tool_backend is None:
			self.logger.warning("工具后端未启用 跳过关闭逻辑")
			return None
		
		await tool_backend.close_backend()
	
	async def on_load(self) -> None:
				
		SHARE_STORE.set(NCATBOT_API, self.api)
		SHARE_STORE.set(PLUGIN_CONFIG, self.config)
		
		await self._register_event_parse_chain()
		await self._register_segment_parse_chain()
		await self._register_tools()
		
		# HACK: 为了快速测试将使用全局单例 技术债
		self.pi_client = await PiClient.open(
			session_dir		= "/tmp/",
			system_prompt	= Path("/sdcard/Ncatbot_QQ/plugins/miaoli_bot/data/prompt_v1.1.md").read_text(),
			buffer_limit	= 32 * 1024 * 1024,
		)
		await self.pi_client.set_model("deepseek-official", "deepseek-flash")
		
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(NCATBOT_API)
		SHARE_STORE.drop(PLUGIN_CONFIG)
		
		await self._close_tool_backend()
				
		if not SHARE_STORE.is_empty():
			self.logger.warning(f"共享容器可能存在资源泄露: {list(SHARE_STORE.keys())}")
	
	@registrar.on_message()
	async def on_message(self, event: MessageEvent) -> None:
		
		is_group		= event.is_group_msg()
		target_id		= get_id_from_event(event)
		event_adapter	= EventAdapter.build(event)
		
		# HACK: 修复了私聊没法使用的问题(需要@ 但私聊不能@) 这里的逻辑还是测试期专属
		if is_group and not event.message.is_at("2449906317"):
			self.logger.warning(f"群消息无3 已跳过")
			return
		
		segment = getattr(event, "message", None)
		if not segment:
			self.logger.warning(f"segment 无内容或 event 不含 segment")
			return
		
		parse_result = await parse_message(event, segment)
		
		i_data = json.dumps({
			"event"		: parse_result.event,
			"segments"	: parse_result.segments,
		}, ensure_ascii=False, indent=2)
		
		
		text	: str = ""
		thinking: str = ""
		
		async for pi_event in self.pi_client.prompt(i_data, streamingBehavior="steer"):
			
			if is_agent_error(pi_event):
				await event_adapter.send(self.api, f"出现错误: {pi_event.error}")
			
			elif is_text_delta(pi_event):
				
				text += pi_event.assistantMessageEvent.delta
				
				# HACK: 不够优雅
				# FIXME: 已知bug 当AI仅回复一句话时，没有`\n\n`，不进入该逻辑，导致最终text被丢弃，可稳定复现
				if text.endswith("\n\n"):
					
					await event_adapter.send(self.api, text.rstrip())
					text = ""
			
			elif is_thinking_delta(pi_event):
				thinking += pi_event.assistantMessageEvent.delta
			
			elif is_agent_end(pi_event):
				
				# HACK: 因为上面的缓冲区bug 临时写一个兜底逻辑 有更好的方案之后将会删除
				if text:
					await event_adapter.send(self.api, text)
					
				await event.reply("[DONE]")
				
				break
		
		return