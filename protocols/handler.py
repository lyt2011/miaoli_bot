from typing	import Protocol, Any


class Handler(Protocol):
		
	async def is_accept(self, data: Any) -> bool: ...
	async def handle(self, data: Any) -> Any: ...