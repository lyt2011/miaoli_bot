from langchain_core.messages	import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from typing	import List, Optional, Tuple


def get_compaction_range(messages: List[BaseMessage]) -> Optional[Tuple[int, int]]:
	
	"""在最后一段用户原话之前 找一段可以拿去压缩的闭区间"""
	
	latest_human = None
	
	for index in range(len(messages) - 1, -1, -1):
		if isinstance(messages[index], HumanMessage):
			latest_human = index
			break
	
	if latest_human is None:
		end = len(messages) - 1
	
	else:
		protected_start = latest_human
		
		while protected_start > 0 and isinstance(messages[protected_start - 1], HumanMessage):
			protected_start -= 1
		
		end = protected_start - 1
	
	start = 0
	for index in range(end + 1):
		if isinstance(messages[index], SystemMessage):
			start = index + 1
	
	while start <= end and isinstance(messages[start], ToolMessage):
		start += 1
	
	if start <= end and isinstance(messages[end], AIMessage) and messages[end].tool_calls:
		end -= 1
	
	if end - start + 1 < 2:
		return None
	
	return start, end
	