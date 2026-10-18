from abc	import ABC, abstractmethod
from typing	import Any

from ..models	import DispatchResult
from ..parsers	import Parser


class ChainProtocol(ABC):
	
	"""解析链协议
	
	一串解析器，按注册顺序询问「你接不接受」，第一个接受的负责产出结果
	"""
	
	@abstractmethod
	def register_parser(self, parser: Parser) -> None: ...
	
	@abstractmethod
	async def dispatch(self, data: Any) -> DispatchResult: ...
