from typing		import Optional, List

from langgraph.config			import get_config
from langchain_core.messages	import AIMessage, ToolCall

from ..consts	import GROUP_PREFIX, PRIVATE_PREFIX


def concatenate_id(session_id: str, is_group: bool) -> str:
	
	prefix = GROUP_PREFIX if is_group else PRIVATE_PREFIX
	
	return f"{prefix}{session_id}"

def split_string(string: str, separator: Optional[str] = None) -> List[str]:
	
	if not separator:
		return [string]
	
	return string.split(separator)

def get_thread_id() -> str:
	
	"""当前会话 id 仅用于日志 图外调用会抛异常 这里兜住"""
	
	try:
		config = get_config()
		return str(config["configurable"]["thread_id"])
	
	except Exception:
		return "unknown"

def get_tool_calls(message: AIMessage) -> List[ToolCall]:
	
	"""取消息里的工具调用 没有就返回空表"""
	
	return message.tool_calls or []
