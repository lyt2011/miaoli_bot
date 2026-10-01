from pydantic				import BaseModel, Field
from typing					import List, Dict, Any
from langchain_core.tools	import tool
from pathlib				import Path
from base64					import b64encode
from hashlib				import md5

from miaoli_bot.stores	import SHARE_STORE
from miaoli_bot.utils	import fail, custom

from ..consts	import PLUGIN_CONFIG
from ..core		import MemeSqlite


class ToolSchema(BaseModel):
	meme_path	: str		= Field(..., description="目标表情包(图片)的路径")
	description	: str		= Field(..., description="表情包的描述，尽可能详细")
	tags		: List[str]	= Field(..., description="表情包的标签", min_length=1)


@tool(args_schema=ToolSchema)
async def archive_meme(meme_path: str, description: str, tags: List[str]) -> Dict[str, Any]:
	
	"""归档表情包"""
	
	plugin_config = SHARE_STORE.recall(PLUGIN_CONFIG)
	
	if not plugin_config.is_enable:
		return fail("meme被禁用")
	
	try:
		
		meme_bytes	= Path(meme_path).read_bytes()
		meme_base64	= b64encode(meme_bytes)
		meme_hash	= md5(meme_base64).hexdigest()
		
		async with MemeSqlite(plugin_config.db_path) as meme_sqlite:
			
			if await meme_sqlite.is_hash_existing(meme_hash):
				meme_info = await meme_sqlite.fetch_meme_from_hash(meme_hash)
				return custom(False, message="该表情包已被归档", description=meme_info["description"], hash=meme_info["hash"])
			
			await meme_sqlite.insert_meme(tags=tags, base64=meme_base64, description=description, hash_=meme_hash)
	
	except Exception as e:
		return fail(f"归档失败: {type(e).__name__}: {e}")

	return custom(True, hash=meme_hash)