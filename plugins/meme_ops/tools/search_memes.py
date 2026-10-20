
from miaoli_bot.api			import store_recall
from langchain_core.tools	import tool
from pydantic				import BaseModel, Field
from typing					import List, Dict, Any

from ..consts	import PLUGIN_CONFIG
from ..core		import MemeSqlite


class ToolSchema(BaseModel):
	tags	: List[str]	= Field(..., description="用于检索的表情包标签", min_length=1)


@tool(args_schema=ToolSchema)
async def search_memes_by_tags(tags: List[str]) -> Dict[str, Any]:
	
	"""
	按标签检索已归档的表情包
	
	返回**同时**带有全部指定标签的表情包
	只带其中一个标签的表情包不会出现在结果里
	"""
	
	try:
		
		async with MemeSqlite(store_recall(PLUGIN_CONFIG).database.path) as meme_sqlite:
			memes = await meme_sqlite.query_tags(tags)
	
	except Exception as e:
		return {"status": False, "message": f"数据库查询失败: {type(e).__name__}: {e}"}
	
	result = {
		meme_id: {
			"hash"			: meme_info["hash"],
			"description"	: meme_info["description"],
			"tags"			: meme_info.get("tags", []),
		}
		for meme_id, meme_info in memes.items()
	}
	
	return {"status": True, "message": result}
