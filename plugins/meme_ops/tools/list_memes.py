
from miaoli_bot.api			import store_recall
from langchain_core.tools	import tool
from typing					import Dict, Any

from ..consts	import PLUGIN_CONFIG
from ..core		import MemeSqlite


@tool
async def list_memes() -> Dict[str, Any]:
	
	"""列出所有已归档的表情包"""
	
	plugin_config	= store_recall(PLUGIN_CONFIG)
	
	if not plugin_config.is_enable:
		return {"status": False, "message": "meme被禁用"}
	
	try:
		
		async with MemeSqlite(plugin_config.db_path) as meme_sqlite:
			rows = await meme_sqlite.fetch_memes()
	
	except Exception as e:
		return {"status": False, "message": f"数据库查询失败: {type(e).__name__}: {e}"}
	
	result = {
		meme_id: {"hash": hash, "description": description}
		for (meme_id, description, hash, _) in rows
	}
	
	return {"status": True, "message": result}