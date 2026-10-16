from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.stores		import SHARE_STORE
from miaoli_bot.consts		import HIGH

from .consts	import PLUGIN_CONFIG, RAW_CONFIG, EVENT_PARSER, SEGMENT_PARSER, REGISTRY
from .chains	import EventParseChain, SegmentParseChain
from .api		import Registry
from .models	import PluginConfig
from .nodes		import event_adapter

from .parsers	import (
	PrivateMessageEventParser,
	GroupMessageEventParser,
	ReplySegmentParser,
	FileSegmentParser,
	QQImageSegmentParser,
	TextSegmentParser,
	AtSegmentParser,
)


class QQAdapterPlugin(PluginProtocol):
	
	"""ncatbot qq 平台适配插件"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		segment_chain	= SegmentParseChain()
		event_chain		= EventParseChain()
		bot_registry	= Registry()
		
		SHARE_STORE.set(PLUGIN_CONFIG, config)
		SHARE_STORE.set(RAW_CONFIG, self.config)
		
		SHARE_STORE.set(SEGMENT_PARSER, segment_chain)
		SHARE_STORE.set(EVENT_PARSER, event_chain)
		SHARE_STORE.set(REGISTRY, bot_registry)
		
		segment_chain.register_parser(ReplySegmentParser())
		segment_chain.register_parser(FileSegmentParser())
		segment_chain.register_parser(QQImageSegmentParser())
		segment_chain.register_parser(TextSegmentParser())
		segment_chain.register_parser(AtSegmentParser())
		
		event_chain.register_parser(PrivateMessageEventParser())
		event_chain.register_parser(GroupMessageEventParser())
		
		self.registry.on_agent_start(event_adapter, priority=HIGH)
	
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
		
		SHARE_STORE.drop(SEGMENT_PARSER)
		SHARE_STORE.drop(EVENT_PARSER)
		SHARE_STORE.drop(REGISTRY)
