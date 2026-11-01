from langchain_core.messages	import AIMessage, BaseMessage

from typing	import List, Set


def declared_tool_call_ids(messages: List[BaseMessage]) -> Set[str]:
	
	"""历史里所有「被发起过」的工具调用 id"""
	
	declared: Set[str] = set()
	
	for message in messages:
		
		if not isinstance(message, AIMessage):
			continue
		
		for tool_call in (message.tool_calls or []):
			declared.add(tool_call["id"])
	
	return declared
