from langgraph.runtime	import Runtime

from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts	import HELPER_TAG, HELPER_TEXT

from typing	import Any, Dict, Optional


async def helper_inject(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	"""把 time-inject 标签的使用说明注入系统提示词"""
	return {"prompts": {HELPER_TAG: HELPER_TEXT}}
