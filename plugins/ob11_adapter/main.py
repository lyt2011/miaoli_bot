from miaoli_bot.api			import store_drop, store_set
from miaoli_bot.protocols	import PluginProtocol
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


class OB11AdapterPlugin(PluginProtocol):
	
	"""ncatbot OB11 事件适配插件"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		segment_chain	= SegmentParseChain()
		event_chain		= EventParseChain()
		bot_registry	= Registry()
		
		store_set(PLUGIN_CONFIG, config)
		store_set(RAW_CONFIG, self.config)
		
		store_set(SEGMENT_PARSER, segment_chain)
		store_set(EVENT_PARSER, event_chain)
		store_set(REGISTRY, bot_registry)
		
		segment_chain.register_parser(ReplySegmentParser())
		segment_chain.register_parser(FileSegmentParser())
		segment_chain.register_parser(QQImageSegmentParser())
		segment_chain.register_parser(TextSegmentParser())
		segment_chain.register_parser(AtSegmentParser())
		
		event_chain.register_parser(PrivateMessageEventParser())
		event_chain.register_parser(GroupMessageEventParser())
		
		self.registry.on_agent_start(event_adapter, priority=HIGH)
	
	async def on_close(self) -> None:
		
		store_drop(PLUGIN_CONFIG)
		store_drop(RAW_CONFIG)
		
		store_drop(SEGMENT_PARSER)
		store_drop(EVENT_PARSER)
		store_drop(REGISTRY)
