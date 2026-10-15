from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.core	import Abort, BaseAction

from langgraph.runtime			import Runtime
from langchain_core.messages	import AIMessage, ToolMessage, HumanMessage
from typing						import Optional


async def output_checker(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[BaseAction]:
	
	"""检查输出类型是否合理"""
	
	messages = state.get("messages")
	if not messages or not isinstance(messages, list):
		return Abort(reason="没有可用消息")
	
	latest_msg = messages[-1]
	
	if isinstance(latest_msg, AIMessage):
		return
	
	elif isinstance(latest_msg, ToolMessage):
		return Abort(reason="AI工具调用未被处理")
	
	elif isinstance(latest_msg, HumanMessage):
		return Abort(reason="AI未产生输出")
	
	return Abort(reason=f"消息列表存在未知类型: {type(latest_msg).__name__}")
