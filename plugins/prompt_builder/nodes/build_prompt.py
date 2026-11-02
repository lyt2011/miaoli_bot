from langchain_core.messages	import BaseMessage, SystemMessage

from langgraph.runtime	import Runtime
from langgraph.types	import Overwrite

from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing	import Any, Dict, List, Optional


async def build_prompt(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""
	通过 prompts 的键与值构建提示词字符串
	并回填到 messages
	"""
	
	messages	: List[BaseMessage]	= state.get("messages", [])
	prompt_array: List[str]			= []
	
	for prompt_key, prompt_content in state.get("prompts", {}).items():
		prompt_array.append(f"<{prompt_key}>\n{prompt_content}\n</{prompt_key}>")
	
	# 稳定排序后再拼接提示词
	prompt_array	= sorted(prompt_array)
	prompt_string	= "\n\n".join(prompt_array)
	
	# 空内容跳过
	if not prompt_string.strip():
		return None
	
	# 空内容/内容一样则跳过注入
	if (
		messages
		and isinstance(messages[0], SystemMessage)
		and messages[0].content == prompt_string
	):
		return None
	
	# 过滤掉 SystemMessage
	messages = [
		message for message in messages
		if not isinstance(message, SystemMessage)
	]
	
	return {"messages": Overwrite([SystemMessage(prompt_string), *messages])}
