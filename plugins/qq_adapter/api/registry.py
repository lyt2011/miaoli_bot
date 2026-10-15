from miaoli_bot.stores	import SHARE_STORE

from ..consts	import EVENT_PARSER, SEGMENT_PARSER
from ..parsers	import Parser


class Registry:
	
	"""qq_adapter 子插件注册器"""
	
	def register_segment_parser(self, parser: Parser) -> None:
		SHARE_STORE.recall(SEGMENT_PARSER).register_parser(parser)
	
	def register_event_parser(self, parser: Parser) -> None:
		SHARE_STORE.recall(EVENT_PARSER).register_parser(parser)
