from rapsqlite	import connect, Connection
from textwrap	import dedent


async def ensure_tags_table(conn: Connection) -> None:
	await conn.execute(dedent("""
		CREATE TABLE IF NOT EXISTS tags (
			tag TEXT NOT NULL
			meme_id 
	"""))

async def ensure_meme_table


async def connect_to_meme_sqlite(path: str) -> Connection:
	
	conn = connect(path)
	
	# 确保