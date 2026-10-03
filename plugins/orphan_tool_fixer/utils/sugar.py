from typing		import List, Set

from langchain_core.messages	import AIMessage, BaseMessage

from miaoli_bot.utils	import get_tool_calls


def declared_tool_call_ids(messages: List[BaseMessage]) -> Set[str]:
	
	"""历史里所有「被发起过」的工具调用 id"""
	
	declared: Set[str] = set()
	
	for message in messages:
		
		if not isinstance(message, AIMessage):
			continue
		
		for tool_call in get_tool_calls(message):
			declared.add(tool_call["id"])
	
	return declared
