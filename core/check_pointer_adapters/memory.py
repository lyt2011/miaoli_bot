from langgraph.checkpoint.memory	import InMemorySaver

from .protocols	import BaseCheckpointerSaverAdapter

from typing	import Self


class InMemoryAdapter(BaseCheckpointerSaverAdapter):
	
	@classmethod
	async def connect(cls, connect_to: str, **kwargs) -> Self:
		return cls(inner=InMemorySaver())
	
	async def close(self) -> None: ...
