from langchain_core.messages	import InvalidToolCall, ToolCall, ToolMessage

from typing	import Union


def fix_tool_message(tool_call: Union[ToolCall, InvalidToolCall], content: str) -> ToolMessage:
	
	"""为悬空的 tool_call 合成一条「工具未执行」的返回"""
	
	return ToolMessage(
		id				= f"auto-fix: {tool_call['id']}",
		tool_call_id	= tool_call["id"],
		name			= tool_call.get("name"),
		status			= "error",
		content			= content,
	)
