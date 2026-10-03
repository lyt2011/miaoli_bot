from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.utils	import get_thread_id

from typing						import Any, Dict, Optional
from ncatbot.utils				import get_log
from langgraph.runtime			import Runtime
from langchain_core.messages	import ToolMessage, RemoveMessage

from ..utils	import declared_tool_call_ids

LOGGER	= get_log("OrphanToolFixer")

async def fix_orphan_tool_message(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""
	修复孤儿工具返回
	存在返回但不存在发起它的 tool_call -> 删掉该返回
	
	只产出定向删除增量 比整表重写更省
	"""
	
	thread_id	= get_thread_id()
	messages	= state.get("messages") or []
	declared	= declared_tool_call_ids(messages)
	
	# 无发起 AIMessage 的 ToolMessage
	orphans	= [message for message in messages if isinstance(message, ToolMessage) and message.tool_call_id not in declared]
	
	if not orphans:
		return None
	
	LOGGER.warning(f"修复 {thread_id} 的 {len(orphans)} 条孤儿 ToolMessage")
	
	return {"messages": [RemoveMessage(id=message.id) for message in orphans]}
