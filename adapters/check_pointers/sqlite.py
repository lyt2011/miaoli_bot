from typing	import Self

import aiosqlite
from langgraph.checkpoint.sqlite.aio	import AsyncSqliteSaver

from ...protocols	import BaseCheckpointerSaverAdapter


class SQLiteAdapter(BaseCheckpointerSaverAdapter):
	
	@classmethod
	async def connect(cls, connect_to: str, **kwargs) -> Self:
		
		connection		= await aiosqlite.connect(connect_to)
		checkpointer	= AsyncSqliteSaver(conn=connection)
		
		await checkpointer.setup()
		
		return cls(inner=checkpointer)
	
	async def close(self) -> None:
		await self.inner.conn.close()
