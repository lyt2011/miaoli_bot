from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing						import Any, Dict, List
from langgraph.runtime			import Runtime
from langgraph.types				import Overwrite
from langchain_core.messages	import BaseMessage, SystemMessage


async def build_prompt(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""
	通过 prompts 的键与值构建提示词字符串
	并回填到 messages
	"""
	
	messages	: List[BaseMessage]	= state.get("messages", [])
	prompt_array: List[str]			= []
	
	for prompt_key, prompt_content in state.get("prompts", {}).items():
		prompt_array.append(f"<{prompt_key}>{prompt_content}</{prompt_key}>")
	
	# 防止 Overwrite 浪费资源 内容一样则跳过注入
	prompt_string: str = "\n\n".join(prompt_array)
	if messages and isinstance(messages[0], SystemMessage) and messages[0].content == prompt_string:
		return None
	
	# 过滤掉 SystemMessage
	messages = [message for message in messages if not isinstance(message, SystemMessage)]
	
	return {"messages": Overwrite([SystemMessage(prompt_string), *messages])}
