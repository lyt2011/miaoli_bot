from miaoli_bot.api			import store_drop, store_set, get_handler_registry
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import HIGH

from .consts	import PLUGIN_CONFIG, RAW_CONFIG, EVENT_PARSER, SEGMENT_PARSER, PARSER_REGISTRY
from .chains	import EventParseChain, SegmentParseChain
from .core		import ParserRegistry
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
		
		segment_chain		= SegmentParseChain()
		event_chain			= EventParseChain()
		parser_registry		= ParserRegistry()
		handler_registry	= get_handler_registry()
		
		store_set(PLUGIN_CONFIG, config)
		store_set(RAW_CONFIG, self.config)
		
		store_set(SEGMENT_PARSER, segment_chain)
		store_set(EVENT_PARSER, event_chain)
		store_set(PARSER_REGISTRY, parser_registry)
		
		segment_chain.register_parser(ReplySegmentParser())
		segment_chain.register_parser(FileSegmentParser())
		segment_chain.register_parser(QQImageSegmentParser())
		segment_chain.register_parser(TextSegmentParser())
		segment_chain.register_parser(AtSegmentParser())
		
		event_chain.register_parser(PrivateMessageEventParser())
		event_chain.register_parser(GroupMessageEventParser())
		
		handler_registry.on_agent_start(event_adapter, priority=HIGH)
	
	async def on_close(self) -> None:
		
		handler_registry = get_handler_registry()
		
		handler_registry.remove_agent_start(event_adapter)
		
		store_drop(PLUGIN_CONFIG)
		store_drop(RAW_CONFIG)
		
		store_drop(SEGMENT_PARSER)
		store_drop(EVENT_PARSER)
		store_drop(PARSER_REGISTRY)
