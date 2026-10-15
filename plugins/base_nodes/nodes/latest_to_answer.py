from miaoli_bot	import GraphRuntimeContext, GraphState
from typing		import Dict, Any

from langgraph.runtime	import Runtime


async def latest_to_answer(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	"""取最后一条消息作为最终回复"""
	return { "final_answer": state["messages"][-1].content }