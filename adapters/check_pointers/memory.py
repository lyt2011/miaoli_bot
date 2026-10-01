from typing	import Self

from langgraph.checkpoint.memory	import InMemorySaver

from ...protocols	import BaseCheckpointerSaverAdapter


class InMemoryAdapter(BaseCheckpointerSaverAdapter):
	
	@classmethod
	async def connect(cls, connect_to: str, **kwargs) -> Self:
		return cls(inner=InMemorySaver())
	
	async def close(self) -> None: ...
