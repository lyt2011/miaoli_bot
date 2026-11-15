from langchain_core.messages	import AIMessage

from langgraph.runtime	import Runtime

from miaoli_bot.core	import Abort
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing	import Any, Dict, Optional


async def messages_to_output(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""把 messages 末条搬成固定出口 output 该节点需要保证内容可被输出"""
	
	messages = state.get("messages", [])
	
	if not messages or not isinstance(messages[-1], AIMessage):
		return Abort(reason="没有任何东西可以被搬运至输出")
	
	for attr in ("tool_calls", "invalid_tool_calls"):
		if getattr(messages[-1], attr, None):
			return Abort(reason="错误的运行时间 工具调用请求未被处理")
	
	return {"output": messages[-1].content}
