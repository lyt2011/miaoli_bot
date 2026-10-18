
from miaoli_bot.api	import store_recall
from ..consts		import EVENT_PARSER, SEGMENT_PARSER
from ..parsers		import Parser


class Registry:
	
	"""qq_adapter 子插件注册器"""
	
	def register_segment_parser(self, parser: Parser) -> None:
		store_recall(SEGMENT_PARSER).register_parser(parser)
	
	def register_event_parser(self, parser: Parser) -> None:
		store_recall(EVENT_PARSER).register_parser(parser)
