from langchain_core.messages	import AIMessage, BaseMessage

from .estimate_text_tokens	import estimate_text_tokens
from .extract_content		import extract_content
from .extract_tool_calls	import extract_tool_calls


def estimate_message_tokens(message: BaseMessage) -> int:
	
	"""粗估单条消息的 token (只算纯文本 图片等多模态内容不计)"""
	
	content	= extract_content(message)
	
	# 对于 AIMessage 使用公式计算需要单独提取 tool calls
	if isinstance(message, AIMessage):
		for tool_call in extract_tool_calls(message):
			content = content + tool_call
	
	return int(estimate_text_tokens(content))
