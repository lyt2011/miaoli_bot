from miaoli_bot.models	import GraphRuntimeContext, GraphState
from miaoli_bot.core	import Abort, BaseAction

from langgraph.runtime			import Runtime
from langchain_core.messages	import AIMessage, ToolMessage, HumanMessage
from typing						import Optional


async def output_checker(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[BaseAction]:
	
	"""检查输出类型是否合理"""
	
	messages = state.get("messages")
	if not messages or not isinstance(messages, list):
		return Abort(reason="上下文列表没有被注入")
	
	latest_msg = messages[-1]
	
	if isinstance(latest_msg, AIMessage):
		return
	
	elif isinstance(latest_msg, ToolMessage):
		return Abort(reason="ToolMessage 不合理地出现在了 message[-1]")
	
	elif isinstance(latest_msg, HumanMessage):
		return Abort(reason="AI未产生输出")
	
	return Abort(reason=f"消息列表存在未知类型: {type(latest_msg).__name__}")
