from .chain		import ChainProtocol
from ..models		import DispatchResult
from ..parsers		import Parser

from typing	import Set, Any


class BaseParserChain(ChainProtocol):
	
	"""解析链的默认实现
	
	内部用 set 存解析器，dispatch 时逐个询问 is_accept
	第一个接受的调用 handle 并返回，全都不接受则 is_handled=False
	"""
	
	def __init__(self) -> None:
		self._parsers: Set[Parser] = set()
	
	def register_parser(self, parser: Parser) -> None:
		self._parsers.add(parser)
	
	async def dispatch(self, data: Any) -> DispatchResult:
		
		for parser in self._parsers:
			
			if not await parser.is_accept(data):
				continue
			
			return DispatchResult(result=await parser.handle(data))
		
		return DispatchResult(is_handled=False)
