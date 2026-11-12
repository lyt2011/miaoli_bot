from langchain_core.messages	import AIMessage

from ..consts	import TOOL_CALL_TEMPLATE

from typing	import List


def extract_tool_calls(message: AIMessage) -> List[str]:

	"""提取 AIMessage 的 tool_calls"""
	
	assert isinstance(message, AIMessage)
	
	tool_calls = [
		TOOL_CALL_TEMPLATE.substitute(name=tc["name"], args=tc["args"])
		for tc in message.tool_calls
	]
	
	return tool_calls
