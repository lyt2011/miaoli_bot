from miaoli_bot.api		import get_prompt
from miaoli_bot.models	import GraphRuntimeContext, GraphState
from typing				import Any, Dict

from langgraph.runtime	import Runtime


async def inject_soul(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""注入人设提示词"""
	
	return {"prompts": {"soul": get_prompt()}}
