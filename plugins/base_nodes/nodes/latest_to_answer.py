from miaoli_bot	import GraphRuntimeContext, GraphState
from typing		import Dict, Any

from langgraph.runtime			import Runtime
from langchain_core.messages	import AIMessage


async def latest_to_answer(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:

	"""取最后一条消息作为最终回复"""

	last_message = state["messages"][-1]
	return {"final_answer": last_message.content if isinstance(last_message, AIMessage) else "我就是Bug."}
