import aiosqlite
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
DELETE_MEME_BY_ID		= "DELETE FROM memes WHERE id = ?"
DELETE_TAGS_BY_MEME_ID	= "DELETE FROM tags WHERE meme_id = ?"

# read-only
HAS_HASH		= "SELECT EXISTS(SELECT 1 FROM memes WHERE hash = ?)"
FETCH_ALL_MEMES	= "SELECT id, description, hash, base64 FROM memes ORDER BY id"
FETCH_MEME_ID_BY_HASH	= "SELECT id FROM memes WHERE hash = ?"
FETCH_MEME_BY_HASH	= """
SELECT id, description, hash, base64
FROM memes
WHERE hash = ?
"""
FETCH_TAGS_BY_MEME_IDS	= "SELECT meme_id, tag FROM tags WHERE meme_id IN ({placeholder}) ORDER BY meme_id, tag"


class MemeSqlite:
	
	"""表情包 sqlite 门面 一次工具调用开一次连接"""
	
	def __init__(self, path: str) -> None:
		self.path	= path
		self.conn	: aiosqlite.Connection
	
	async def __aenter__(self) -> Self:
		
		self.conn = await aiosqlite.connect(self.path)
		
		await self.conn.execute(ENABLE_FOREIGN)
		await self.conn.execute(CREATE_MEMES_TABLE)
		await self.conn.execute(CREATE_TAGS_TABLE)
		await self.conn.execute(IDX_TAGS_MEMEID)
		
		return self
	
	async def __aexit__(self, exc_type, exc, tb) -> Optional[bool]:
		await self.conn.commit()
		await self.conn.close()
	
	# ------------------------------------------------------------------ 读
	
	async def fetch_memes(self) -> List[Tuple[int, str, str, bytes]]:
		
		"""取全部表情包 (id, description, hash, base64)"""
		
		cur		= await self.conn.execute(FETCH_ALL_MEMES)
		rows	= await cur.fetchall()
		
		return rows
	
	async def fetch_meme_by_hash(self, hash_: str) -> Optional[Dict[str, Any]]:
		
		"""按 hash 取单个表情包 找不到返回 None"""
		
		cur		= await self.conn.execute(FETCH_MEME_BY_HASH, (hash_, ))
		rows	= await cur.fetchall()
		
		if rows:
			meme_id, description, _hash, base64 = rows[0]
			return {"id": meme_id, "description": description, "hash": _hash, "base64": base64}
	
	async def fetch_tags_by_meme_ids(self, meme_ids: List[int]) -> Dict[int, List[str]]:
		
		"""按 meme_id 批量取标签 顺序按 (meme_id, tag) 排好"""
		
		meme_ids = tuple(dict.fromkeys(meme_ids))
		
		if not meme_ids:
			return {}
		
		placeholder = ", ".join("?" * len(meme_ids))
		command		= FETCH_TAGS_BY_MEME_IDS.format(placeholder=placeholder)
		
		cur		= await self.conn.execute(command, meme_ids)
		rows	= await cur.fetchall()
		
		tags: Dict[int, List[str]] = {}
		
		for (meme_id, tag) in rows:
			tags.setdefault(meme_id, []).append(tag)
		
		return tags
	
	async def has_hash(self, hash_: str) -> bool:
		
		"""hash 是否已归档"""
		
		cur		= await self.conn.execute(HAS_HASH, (hash_, ))
		rows	= await cur.fetchall()
		
		return bool(rows[0][0])
	
	# ------------------------------------------------------------------ 写
	
	async def add_meme(self, *, tags: List[str], base64: bytes, description: str, hash_: str) -> None:
		
		"""归档一个表情包并写入它的标签"""
		
		cur = await self.conn.execute(INSERT_NEW_MEME, (description, base64, hash_))
		await self.conn.executemany(INSERT_NEW_TAG, ((tag, cur.lastrowid) for tag in dict.fromkeys(tags)))
		
		await self.conn.commit()
	
	async def remove_meme(self, hash_: str) -> Optional[int]:
		
		"""通过 hash 删除表情包与其标签引用 找不到返回 None"""
		
		cur		= await self.conn.execute(FETCH_MEME_ID_BY_HASH, (hash_, ))
		rows	= await cur.fetchall()
		
		if not rows:
			return None
		
		meme_id = rows[0][0]
		
		# 外键开启 必须先删 tag 引用再删 meme 反过来会被外键拒绝
		await self.conn.execute(DELETE_TAGS_BY_MEME_ID, (meme_id, ))
		await self.conn.execute(DELETE_MEME_BY_ID, (meme_id, ))
		
		await self.conn.commit()
		
		return meme_id
