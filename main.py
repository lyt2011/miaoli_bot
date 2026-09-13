from ncatbot.plugin		import NcatBotPlugin
from ncatbot.core		import registrar
from ncatbot.event.qq	import MessageEvent
from ncatbot.utils		import get_log

from pi_bridge	import models
from pathlib	import Path

from .chains	import EventParseChain, SegmentParseChain
from .core		import PIToolBackend, PiClient
from .parsers	import (
	GroupMessageEventParser,
	PrivateMessageEventParser,
	AtSegmentParser,
	TextSegmentParser,
)
from .stores	import SHARE_STORE
from .tools		import send_message_to_QQ, download_qq_file
from .adapters	import EventAdapter
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
)

import json
import asyncio


class Claw(NcatBotPlugin):
	
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
		
	async def _register_tools(self) -> None:
		
		"""统一注册工具"""
		
		async with self._plugin_lock:
			
			if not hasattr(self, "config"):
				raise RuntimeError(f"调用时序出错 config不可用")
			
			config = self.config
		
		async with self._share_store_lock:
		
			if SHARE_STORE.contains(TOOL_BACKEND):
				return None
		
			tool_backend = PIToolBackend(config)
			SHARE_STORE.set(TOOL_BACKEND, tool_backend)
		
		tool_backend.register_tool(send_message_to_QQ)
		tool_backend.register_tool(download_qq_file)
		
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
		
		await self._register_event_parse_chain()
		await self._register_segment_parse_chain()
		await self._register_tools()
		
		# HACK: 为了快速测试留下的技术债
		self.pi_client = await PiClient.open(
			session_dir		= "/tmp/",
			system_prompt	= Path("/sdcard/Ncatbot_QQ/plugins/miaoli_bot/data/prompt_v1.1.md").read_text(),
			buffer_limit	= 32 * 1024 * 1024,
		)
		await self.pi_client.set_model("deepseek-official", "deepseek-flash")
		
	async def on_close(self) -> None:
		
		await self._close_tool_backend()
				
		if not SHARE_STORE.is_empty():
			self.logger.warning(f"共享容器可能存在资源泄露: {list(SHARE_STORE.keys())}")
	
	@registrar.on_message()
	async def on_message(self, event: MessageEvent) -> None:
		
		is_group		= event.is_group_msg()
		target_id		= get_id_from_event(event)
		event_adapter	= EventAdapter.build(event)
		
		# HACK: 测试期过滤非@
		if not event.message.is_at("2449906317"):
			self.logger.warning(f"跳过 非@")
			return
		
		# HACK: 测试期白名单
		if target_id not in ("1046279455", "3757973483"):
			self.logger.warning(f"跳过 {target_id}")
			return
		
		# HACK: 这里可能不稳定 需要先判断再获取属性
		parse_result = await parse_message(event, event.message)
		
		i_data = json.dumps({
			"event"		: parse_result.event,
			"segments"	: parse_result.segments,
		}, ensure_ascii=False, indent=2)
		
		
		client_state = await self.pi_client.get_state()
		if client_state.isStreaming is True:
			return await self.pi_client.steer(i_data)
		
		
		text	: str = ""
		thinking: str = ""
		
		async for pi_event in self.pi_client.prompt(i_data):
			
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
				
				# HACK: 因为上面的缓冲区bug 临时写一个兜底逻辑
				if text:
					await event_adapter.send(self.api, text)
				
				break
		
		# 思维链懒得看了 先删掉
		# if thinking:
			# await event_adapter.send(self.api, f"=====思维链=====\n\n{thinking}")
		
		await event.reply("[DONE]")