from miaoli_bot	import GraphRuntimeContext, GraphState
from typing		import Dict, Any

from langgraph.runtime			import Runtime
from langgraph.config			import get_config
from langchain_core.messages	import AIMessage


async def latest_to_answer(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:

	"""取最后一条消息作为最终回复"""
	
	last_message = state["messages"][-1]
	
	if isinstance(last_message, AIMessage):
		return { "final_answer": last_message.content }
	
	config		= get_config()
	thread_id	= config["configurable"].get("thread_id", "unknown")
	
	return { "final_answer": f"最后一条非 AIMessage 信息 ({type(last_message).__name__})\n请携带 thread_id={thread_id} 向管理员反馈" }
