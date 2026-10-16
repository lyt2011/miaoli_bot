from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.stores	import SHARE_STORE
from miaoli_bot.utils	import get_tool_calls

from typing						import Any, Dict, Optional
from langgraph.runtime			import Runtime
from langgraph.types			import Overwrite
from langchain_core.messages	import AIMessage, ToolMessage

from ..consts	import PLUGIN_CONFIG
from ..utils	import fix_tool_message


async def fix_pending_tool_call(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""修复悬空的工具调用"""
	
	plugin_cfg	= SHARE_STORE.recall(PLUGIN_CONFIG)
	
	# 没有数据就不修复
	if "messages" not in state:
		return None
	
	# 获取数据
	messages	= state["messages"]
	
	# 记录修复数量
	fixed		= 0
	repaired	= []
	answered	= {message.tool_call_id for message in messages if isinstance(message, ToolMessage)}
	
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
		return {"messages": Overwrite(repaired)}
