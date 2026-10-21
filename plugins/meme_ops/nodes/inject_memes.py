from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing				import Any, Dict
from langgraph.runtime	import Runtime

from ..consts	import PLUGIN_CONFIG
from ..core		import MemeSqlite


async def inject_memes(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""使 meme 常驻提示词 而不是每次强制读取"""

	async with MemeSqlite(store_recall(PLUGIN_CONFIG).database.path) as meme_sqlite:
		rows = await meme_sqlite.fetch_memes()
	
	memes = [
		f"{hash}: {description}"
		for (meme_id, description, hash, _) in rows
	]
	
	return {"prompts": {"available_memes": "\n".join(memes)}}
