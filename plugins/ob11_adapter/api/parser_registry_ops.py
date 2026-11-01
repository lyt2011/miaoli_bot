from miaoli_bot.api	import store_recall

from ..core		import ParserRegistry
from ..consts	import PARSER_REGISTRY


def get_parser_registry() -> ParserRegistry:
	"""取解析器注册器"""
	return store_recall(PARSER_REGISTRY)
