from miaoli_bot.api			import store_recall
from pydantic				import BaseModel, Field
from typing					import Dict, Any
from langchain_core.tools	import tool


from ..consts	import PLUGIN_CONFIG
from ..core		import MemeSqlite


class ToolSchema(BaseModel):
	hash	: str	= Field(..., description="待删除表情包的 hash")


@tool(args_schema=ToolSchema)
async def remove_meme_by_hash(hash: str) -> Dict[str, Any]:
	
	"""
	通过 hash 删除一个已归档的表情包
	
	表情包本体与其对应的全部标签引用都会被一并删除
	删除后无法通过 send_meme_to_qq 发送
	"""
	
	try:
		
		async with MemeSqlite(store_recall(PLUGIN_CONFIG).database.path) as meme_sqlite:
			
			meme_info	= await meme_sqlite.fetch_meme_from_hash(hash)
			meme_id		= await meme_sqlite.remove_meme(hash)
	
	except Exception as e:
		return {"status": False, "message": f"删除失败: {type(e).__name__}: {e}"}
	
	if meme_id is None:
		return {"status": False, "message": f"找不到 hash 为 {hash} 的表情包"}
	
	return {"status": True, "meme_id": meme_id, "description": meme_info["description"]}
