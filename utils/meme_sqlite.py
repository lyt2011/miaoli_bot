from rapsqlite	import connect
from typing		import Self, Optional, List, Dict, Any, Tuple


# creater
CREATE_MEMES_TABLE = """
CREATE TABLE IF NOT EXISTS memes (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	description TEXT NOT NULL,
	base64 TEXT NOT NULL UNIQUE,
	hash TEXT NOT NULL UNIQUE
)
"""
CREATE_TAGS_TABLE = """
CREATE TABLE IF NOT EXISTS tags (
	tag TEXT NOT NULL CHECK (TRIM(tag) != ''),
	meme_id INTEGER NOT NULL,
	FOREIGN KEY (meme_id) REFERENCES memes(id),
	PRIMARY KEY (tag, meme_id)
)
"""
IDX_TAGS_MEMEID	= "CREATE INDEX IF NOT EXISTS idx_tags_meme ON tags(meme_id)"

# setter
ENABLE_FOREIGN	= "PRAGMA foreign_keys = ON"

# write-only
INSERT_NEW_MEME	= "INSERT INTO memes (description, base64, hash) VALUES (?, ?, ?)"
INSERT_NEW_TAG	= "INSERT INTO tags (tag, meme_id) VALUES (?, ?)"

# read-only
CHECK_HASH_EXISTENCE	= "SELECT EXISTS(SELECT 1 FROM memes WHERE hash = ?)"
FETCH_ALL_MEME			= "SELECT id, description, hash, base64 FROM memes"
FETCH_MEME_ID_BY_HASH	= """
SELECT id, description, hash, base64
FROM memes
WHERE hash = ?
"""


class MemeSqlite:
	
	def __init__(self, path: str) -> None:
		self.conn = connect(path)
	
	async def query_tags(self, tags: List[str]) -> Dict[str, Any]:
		
		meme_ids	= await self._fetch_meme_ids_from_tags(tags)
		memes		= await self._fetch_meme_infos_from_tags(meme_ids)
		tags		= await self._fetch_tags_from_meme_ids(meme_ids)
		
		for meme_id in tuple(memes.keys()):
			if meme_id in tags:
				memes[meme_id]["tags"] = tags[meme_id]
		
		return memes
	
	async def fetch_memes(self) -> List[Tuple[str, str, str, str]]:
		
		cur		= await self.conn.execute(FETCH_ALL_MEME)
		rows	= await cur.fetchall()
		
		return rows
	
	async def fetch_meme_from_hash(self, hash_: str) -> Optional[Dict[str, Any]]:
		
		cur		= await self.conn.execute(FETCH_MEME_ID_BY_HASH, (hash_, ))
		rows	= await cur.fetchall()
		
		if rows:
			meme_id, description, _hash, base64 = rows[0]
			return {"id": meme_id, "description": description, "hash": _hash, "base64": base64}
		
	async def is_hash_existing(self, hash_: str) -> bool:
		cur		= await self.conn.execute(CHECK_HASH_EXISTENCE, (hash_, ))
		rows	= await cur.fetchall()
		return bool(rows[0][0])
	
	async def insert_meme(self, *, tags: List[str], base64: str, description: str, hash_: str) -> None:
		
		# 插入新meme并插入对应tag
		cur = await self.conn.execute(INSERT_NEW_MEME, (description, base64, hash_))
		await self.conn.executemany(INSERT_NEW_TAG, ((tag, cur.lastrowid) for tag in set(tags)))
		
		await self.conn.commit()
	
	async def __aenter__(self) -> Self:
		
		await self.conn.execute(ENABLE_FOREIGN)
		await self.conn.execute(CREATE_MEMES_TABLE)
		await self.conn.execute(CREATE_TAGS_TABLE)
		await self.conn.execute(IDX_TAGS_MEMEID)
		
		return self
	
	async def __aexit__(self, exc_type, exc, tb) -> Optional[bool]:
		await self.conn.commit()
		await self.conn.close()
	
	async def _fetch_meme_ids_from_tags(self, tags: List[str]) -> List[str]:
		
		"""通过 tags 找 meme_id"""
		
		tags		= tuple(set(tags))
		tags_len	= len(tags)
		
		placeholder = ", ".join("?" * tags_len)
		command		= (
			"SELECT meme_id "
			"FROM tags "
			f"WHERE tag IN ({placeholder}) "
			"GROUP BY meme_id "
			f"HAVING COUNT(DISTINCT tag) = {tags_len}"
		)
		
		cur		= await self.conn.execute(command, tags)
		rows	= await cur.fetchall()
		
		return [row[0] for row in rows]
	
	async def _fetch_meme_infos_from_tags(self, meme_ids: List[str]) -> Dict[str, Dict[str, Any]]:
		
		"""内部接口 耦合没办法"""
		
		meme_ids = tuple(set(meme_ids))
		
		placeholder = ", ".join("?" * len(meme_ids))
		command		= (
			"SELECT id, description, base64 "
			"FROM memes "
			f"WHERE id IN ({placeholder})"
		)
		
		cur		= await self.conn.execute(command, meme_ids)
		rows	= await cur.fetchall()
		
		return {
			meme_id: { "description": description, "base64": base64 }
			for (meme_id, description, base64) in rows
		}
	
	async def _fetch_tags_from_meme_ids(self, meme_ids: List[str]) -> Dict[str, List[str]]:
		
		"""内部接口 获取 meme_id 对应的所有 tags"""
		
		meme_ids = tuple(set(meme_ids))
		
		placeholder = ", ".join("?" * len(meme_ids))
		command		= (
			"SELECT meme_id, GROUP_CONCAT(tag, '§') "
			"FROM tags "
			f"WHERE meme_id IN ({placeholder}) "
			"GROUP BY meme_id"
		)
		
		cur		= await self.conn.execute(command, meme_ids)
		rows	= await cur.fetchall()
		
		return {meme_id: tags.split("§") for (meme_id, tags) in rows}