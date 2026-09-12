from ..protocols	import ChainProtocol, Handler
from ..models		import DispatchResult

from typing	import Set, Any


class BaseHandlerChain(ChainProtocol):
	
	def __init__(self) -> None:
		
		self._handlers: Set[Handler] = set()
		
	def register_handler(self, handler: Handler) -> None:
		self._handlers.add(handler)
		
	async def dispatch(self, data: Any) -> DispatchResult:
		
		for handler in self._handlers:
			
			if not await handler.is_accept(data):
				continue
			
			return DispatchResult(result=await handler.handle(data))
		
		return DispatchResult(is_handled=False)
