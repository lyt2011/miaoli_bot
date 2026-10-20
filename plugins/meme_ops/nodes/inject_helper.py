from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing				import Any, Dict
from langgraph.runtime	import Runtime

from ..consts	import PLUGIN_CONFIG


async def inject_helper(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""注入表情包使用提示"""
	
	return {"prompt": {"meme_helper": store_recall(PLUGIN_CONFIG).helper}}
