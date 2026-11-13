from langchain_core.messages	import AIMessage, BaseMessage

from .estimate_content_tokens	import estimate_content_tokens
from .estimate_text_tokens	import estimate_text_tokens
from .extract_tool_calls	import extract_tool_calls


def estimate_message_tokens(message: BaseMessage) -> float:
	
	"""粗估单条消息的 token (正文与多模态内容都计入) 返回未取整的 float 取整交给调用方"""
	
	tokens	= estimate_content_tokens(message.content)
	
	# 对于 AIMessage 使用公式计算需要单独提取 tool calls
	if isinstance(message, AIMessage):
		for tool_call in extract_tool_calls(message):
			tokens = tokens + estimate_text_tokens(tool_call)
	
	return tokens
