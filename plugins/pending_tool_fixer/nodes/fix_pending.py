from langchain_core.messages	import AIMessage, ToolMessage

from langgraph.runtime	import Runtime
from langgraph.types	import Overwrite

from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts	import COMMON_FIX_TEXT, INVALID_FIX_TEXT
from ..utils	import fix_tool_message

from typing	import Any, Dict, Optional

import logging


LOGGER = logging.getLogger("PendingToolFixer")


async def fix_pending_tool_call(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""通过新增 ToolMessage 修复正确/错误悬空的工具调用"""
		
	# 拿上下文
	messages = state.get("messages")
	if not messages:
		return None
	
	# 重新放置的 / 所有存在的 tool_call_id
	repaired	= []
	answered	= [message.tool_call_id for message in messages if isinstance(message, ToolMessage)]
	
	for message in messages:
		
		# 先把原 message 塞回去上下文
		repaired.append(message)
		
		# 对于非 AIMessage 跳过修复
		if not isinstance(message, AIMessage):
			continue
		
		# 先修复正确的 schema 的悬空 tool_call
		for tc in (message.tool_calls or []):
			if tc["id"] not in answered:
				repaired.append(fix_tool_message(tc, COMMON_FIX_TEXT))
		
		# 然后修复错误 schema 的悬空 tool_call
		for tc in (message.invalid_tool_calls or []):
			if tc["id"] not in answered:
				repaired.append(fix_tool_message(tc, INVALID_FIX_TEXT))
	
	if len(repaired) == len(messages):
		return None
	
	LOGGER.warning("修复了 "
		f"{len(repaired) - len(messages)} 个错误/正确 schema 的悬空 tool call")
	
	return {"messages": Overwrite(repaired)}
