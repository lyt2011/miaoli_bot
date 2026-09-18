from typing	import Protocol, runtime_checkable


@runtime_checkable
class Closable(Protocol):
	
	async def close(self) -> None: ...