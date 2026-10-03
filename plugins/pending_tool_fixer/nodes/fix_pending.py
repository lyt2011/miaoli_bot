from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.stores	import SHARE_STORE
from miaoli_bot.utils	import get_thread_id, get_tool_calls

from typing						import Any, Dict, List, Optional
from ncatbot.utils				import get_log
from langgraph.runtime			import Runtime
from langgraph.types			import Overwrite
from langchain_core.messages	import AIMessage, ToolMessage

from ..consts	import PLUGIN_CONFIG
from ..utils	import fix_tool_message


LOGGER	= get_log("PendingToolFixer")


async def fix_pending_tool_call(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""修复悬空的工具调用"""
	
	plugin_cfg	= SHARE_STORE.recall(PLUGIN_CONFIG)
	
	if "messages" not in state:
		return None
	
	messages	= state["messages"]
	thread_id	= get_thread_id()
	answered	= {message.tool_call_id for message in messages if isinstance(message, ToolMessage)}
	
	repaired	: List[Any] = []
	fixed		= 0
	
	for message in messages:
		
		repaired.append(message)
		
		if not isinstance(message, AIMessage):
			continue
		
		for tool_call in get_tool_calls(message):
			
			if tool_call["id"] in answered:
				continue
			
			fixed += 1
			repaired.append(fix_tool_message(tool_call, plugin_cfg.fix_message))
	
	if fixed:
		LOGGER.warning(f"修复 {thread_id} 的 {fixed} 条悬空工具调用")
		return {"messages": Overwrite(repaired)}