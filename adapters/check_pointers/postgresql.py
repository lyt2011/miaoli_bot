from typing	import Self

from psycopg.rows						import DictRow, RowMaker, dict_row
from psycopg_pool						import AsyncConnectionPool
from langgraph.checkpoint.base			import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio	import AsyncPostgresSaver

from ...protocols	import BaseCheckpointerSaverAdapter


class PostgresqlAdapter(BaseCheckpointerSaverAdapter):
	
	def __init__(self, inner: BaseCheckpointSaver, pool: AsyncConnectionPool) -> None:
		
		super().__init__(inner=inner)
		
		self._pool = pool
	
	@classmethod
	async def connect(cls, connect_to: str, **kwargs) -> Self:
		
		autocommit	: bool				= kwargs.get("autocommit", True)
		max_size	: int				= kwargs.get("max_size", 8)
		min_size	: int				= min(kwargs.get("min_size", 4), max_size)
		row_factory	: RowMaker[DictRow]	= kwargs.get("row_factory", dict_row)
		
		conn_pool	= AsyncConnectionPool(
			conninfo	= connect_to,
			max_size	= max_size,
			min_size	= min_size,
			open		= False,
			kwargs		= {"autocommit": autocommit, "row_factory": row_factory}
		)
		
		await conn_pool.open()
		checkpointer = AsyncPostgresSaver(conn_pool)
		await checkpointer.setup()
		
		return cls(inner=checkpointer, pool=conn_pool)
	
	async def close(self) -> None:
		await self._pool.close()