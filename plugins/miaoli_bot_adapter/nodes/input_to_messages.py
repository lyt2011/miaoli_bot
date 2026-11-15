from langchain_core.messages	import HumanMessage

from langgraph.runtime	import Runtime

from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing	import Any, Dict, Optional


async def input_to_messages(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""把固定入口 input 搬成一条 HumanMessage 追加进 messages"""
	
	content = state.get("input")
	
	# 没有输入就不动 messages
	if not content:
		return None
	
	return {"messages": [HumanMessage(content)]}
