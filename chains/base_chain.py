from ..protocols	import ChainProtocol, Parser
from ..models		import DispatchResult

from typing	import Set, Any


class BaseParserChain(ChainProtocol):
	
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
