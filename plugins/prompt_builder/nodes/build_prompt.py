from langchain_core.messages	import SystemMessage

from langgraph.runtime	import Runtime
from langgraph.types	import Overwrite

from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..utils	import to_xml_prompt

from typing	import Any, Dict, Optional

import logging


LOGGER = logging.getLogger("PromptBuilder")


async def build_prompt(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""
	通过 prompts 的键与值构建提示词字符串
	并回填到 messages
	"""
	
	messages	= state.get("messages", [])
	prompts		= state.get("prompts", {})
	
	# 构建提示词数组 按照长度排序(越长放越前面) 拼接提示词
	prompt_array	= [to_xml_prompt(key, value) for key, value in prompts.items()]
	prompt_array	= sorted(prompt_array, key=lambda s: len(s), reverse=True)
	prompt_string	= "\n\n".join(prompt_array).strip()
	
	# 空内容跳过
	if not prompt_string:
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
