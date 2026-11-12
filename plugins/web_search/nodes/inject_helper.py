from langgraph.runtime	import Runtime

from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts	import HELPER_PROMPT

from typing	import Any, Dict


async def inject_helper(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	"""把联网搜索的使用说明写进提示词段"""
	return {"prompts": {"web-search-helper": HELPER_PROMPT}}
