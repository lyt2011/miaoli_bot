from ncatbot.plugin		import NcatBotPlugin
from ncatbot.core		import registrar
from ncatbot.event.qq	import MessageEvent

from pi_bridge	import models
from pathlib	import Path
from typing		import Callable, Awaitable

from .chains	import EventParseChain, SegmentParseChain
from .core		import PIToolBackend, PiClient, PiSessionManager
from .stores	import SHARE_STORE
from .adapters	import EventAdapter
from .protocols	import Closable
from .models	import PluginConfig
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
	query_qq_message_id,
	delete_qq_message,
)
from .utils		import (
	easier_send,
	parse_message,
	get_id_from_event,
	is_agent_end,
	is_agent_error,
	is_thinking_delta,
	is_text_delta,
	concatenate_id,
)
from .consts	import (
	EVENT_PARSER,
	SEGMENT_PARSER,
	NCATBOT_API,
	TOOL_BACKEND,
	PLUGIN_CONFIG,
	PI_SESSION_MANAGER,
	RAW_CONFIG,
)

import json
import asyncio


PLUGIN_NAME	= "喵璃の本体"


class MiaoLiBot(NcatBotPlugin):
	
	def __init__(self, *args, **kwargs) -> None:
		
		super().__init__(*args, **kwargs)
		
		self._share_store_lock	= asyncio.Lock()
		self._plugin_lock		= asyncio.Lock()
		
		self.cfg: Optional[PluginConfig]	= None
	
	async def _register_session_manager(self) -> None:
		
		"""SessionManager 不会被二次注册"""
		
		async with self._share_store_lock:
			
			if SHARE_STORE.contains(PI_SESSION_MANAGER):
				return None
			
			session_manager = PiSessionManager()
			SHARE_STORE.set(PI_SESSION_MANAGER, session_manager)
		
		return None
	
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
		tool_backend.register_tool(delete_qq_message)
		
		await tool_backend.run_server()
	
	async def _close_tool_backend(self) -> None:
		
		async with self._share_store_lock:
			
			tool_backend = SHARE_STORE.recall(TOOL_BACKEND, None)
			
			if tool_backend is not None:
				SHARE_STORE.drop(TOOL_BACKEND)
		
		# double-check并打印日志
		if tool_backend is None:
			self.logger.warning("工具后端未启用 跳过关闭逻辑")
			return
		
		await tool_backend.close_backend()
	
	async def _close_session_manager(self) -> None:
		
		async with self._share_store_lock:
			
			session_manager = SHARE_STORE.recall(PI_SESSION_MANAGER, None)
			
			if session_manager is not None:
				SHARE_STORE.drop(PI_SESSION_MANAGER)
		
		if session_manager is None:
			self.logger.warning("SessionManager 未启用 跳过关闭逻辑")
			return
		
		await session_manager.close()
	
	async def create_pi_factory(self, session_id: str) -> Callable[[], Awaitable[PiClient]]:
		
		"""
		按插件配置闭包出目标会话的无参建连工厂
		工厂只在会话未命中时被 PiSessionManager 调用
		session_dir / buffer_limit / system_prompt（由 prompt_file 推导）/
		provider / model_id 全部来自插件配置模型 self.cfg
		"""
		
		session_dir		= getattr(self.cfg, "session_dir", "/tmp")
		buffer_limit	= getattr(self.cfg, "buffer_limit", 32 * 1024 * 1024)
		system_prompt	= getattr(self.cfg, "system_prompt", None)
		provider		= getattr(self.cfg, "provider")
		model_id		= getattr(self.cfg, "model_id")
		
		async def pi_factory() -> PiClient:
			
			pi_client = await PiClient.open(
				session_id		= session_id,
				session_dir		= session_dir,
				system_prompt	= system_prompt,
				buffer_limit	= buffer_limit,
			)
			
			await pi_client.set_model(provider=provider, model_id=model_id)
			
			return pi_client
		
		return pi_factory
	
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
		
		await self._register_event_parse_chain()
		await self._register_segment_parse_chain()
		await self._register_tools()
		await self._register_session_manager()
				
		self.logger.info(f"{PLUGIN_NAME} 已加载")
		
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(NCATBOT_API)
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
		
		await self._close_tool_backend()
		await self._close_session_manager()
		
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
		
		
		if is_group and not event.message.is_at("2449906317"):
			self.logger.warning(f"群消息无3 已跳过")
			return
		
		session_manager = SHARE_STORE.recall(PI_SESSION_MANAGER, None)
		if session_manager is None:
			self.logger.warning("SessionManager 不可用 跳过")
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
		
		session_id = concatenate_id(target_id, is_group=is_group)
		
		
		factory		= await self.create_pi_factory(session_id)
		pi_client	= await session_manager.ensure_session(factory=factory, session_id=session_id)
		
		text	: str = ""
		thinking: str = ""
		
		async for pi_event in pi_client.prompt(i_data, streamingBehavior="steer"):
			
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
			
			else:
				self.logger.warning(f"未被处理的 event -> {type(pi_event).__name__}")
		
		return