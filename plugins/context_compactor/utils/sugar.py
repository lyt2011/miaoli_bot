from typing						import Any, List
from langchain_core.messages	import AIMessage, HumanMessage, SystemMessage

from .block_ops					import handle_block


def keep_recent_messages(messages: List[Any], n: int) -> List[Any]:
	
	"""
	保留最近 n 条有效信息
	ToolMessage 不会增加数量
	"""
	
	recent_messages	: List[Any] = []
	message_count	: int		= 0
	
	if not messages or n <= 0:
		return recent_messages
		
	for message in messages[::-1]:
		
		recent_messages.insert(0, message)
		
		if isinstance(message, (AIMessage, SystemMessage, HumanMessage)):
			message_count += 1
		
		if message_count >= n:
			break
	
	return recent_messages

def merge_contents(messages: List[Any]) -> str:
	
	"""
	合并content的内容
	不算也不能强行str 防止重复压缩
	"""
	
	contents: str = ""
	
	for message in messages:
		
		if hasattr(message, "content") and message.content:
			
			if isinstance(message.content, list):
				contents += handle_block(message.content)
			
			elif isinstance(message.content, str):
				contents += message.content
		
		if hasattr(message, "tool_calls") and message.tool_calls:
			contents += str(message.tool_calls)
	
	return contents
