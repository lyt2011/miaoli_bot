from langchain_core.messages	import BaseMessage

from langgraph.runtime	import Runtime

from miaoli_bot.core	import Goto
from miaoli_bot.consts	import ON_TOOL_CALLING, ON_TURN_END
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing	import List


def is_tool_calling(messages: List[BaseMessage]) -> bool:
	"""末条消息是否带工具调用"""
	return bool(messages and getattr(messages[-1], "tool_calls", None))


async def on_after_request(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	
	messages	= state.get("messages") or []
	goto		= ON_TOOL_CALLING if is_tool_calling(messages) else ON_TURN_END
	
	return Goto(goto=goto)
