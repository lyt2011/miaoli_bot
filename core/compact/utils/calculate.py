from langchain_core.messages	import AIMessage, BaseMessage

from .extract_content		import extract_content
from .extract_tool_calls	import extract_tool_calls


def base_calculate(message: BaseMessage) -> int:
	
	"""计算 BaseMessage 的 token (基于公式)"""
	
	content	= extract_content(message)
	
	# 对于 AIMessage 使用公式计算需要单独提取 tool calls
	if isinstance(message, AIMessage):
		for tool_call in extract_tool_calls(message):
			content = content + tool_call
	
	# NOTE: 公式最简实现 能用但不咋好用
	return int(len(content) * 0.47)