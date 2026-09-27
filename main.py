from ncatbot.plugin		import NcatBotPlugin
from ncatbot.core		import registrar
from ncatbot.event.qq	import MessageEvent

from pathlib	import Path
from typing		import Callable, Awaitable

from .chains	import EventParseChain, SegmentParseChain
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
from .utils		import (
	easier_send,
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
		
		self.logger.info(f"{PLUGIN_NAME} 已加载")
		
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(NCATBOT_API)
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
		
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
		
		
		if is_group and not event.message.is_at("2449906317", all_except=True):
			self.logger.warning(f"群消息无@ 已跳过")
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
		
		
		# TODO: 以下逻辑需要重写
		# TODO: 以下逻辑需要重写
		# TODO: 以下逻辑需要重写
		# TODO: 以下逻辑需要重写
		# TODO: 以下逻辑需要重写
		# TODO: 以下逻辑需要重写
		# TODO: 以下逻辑需要重写