from typing	import Protocol, Any, runtime_checkable


@runtime_checkable
class Parser(Protocol):
		
	async def is_accept(self, data: Any) -> bool: ...
	async def handle(self, data: Any) -> Any: ...