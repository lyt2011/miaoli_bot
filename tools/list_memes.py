from ..consts	import PLUGIN_CONFIG
from ..stores	import SHARE_STORE
from ..utils	import fail, success, MemeSqlite

from langchain_core.tools	import tool
from typing					import Dict, Any


@tool
async def list_memes() -> Dict[str, Any]:
	
	"""列出所有已归档的表情包"""
	
	plugin_config	= SHARE_STORE.recall(PLUGIN_CONFIG, None)
	meme_config		= getattr(plugin_config, "meme_config", None)
	if meme_config is None or not meme_config.is_enable:
		return fail("meme被禁用")
	
	async with MemeSqlite(meme_config.db_path) as meme_sqlite:
		rows = await meme_sqlite.fetch_memes()
	
	result = {
		meme_id: {"hash": hash, "description": description}
		for (meme_id, description, hash, _) in rows
	}
	
	return success(result)