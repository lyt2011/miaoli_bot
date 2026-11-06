from langchain_core.messages	import AIMessage, HumanMessage

from langgraph.runtime	import Runtime

from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts	import PLUGIN_CONFIG
from ..utils	import build_prompt, content_to_text

from typing		import Any, Dict, Optional

import logging


LOGGER	= logging.getLogger()
GUIDE	= "以下本轮的意图识别注入内容。"
TAG		= "intent-recognition"


async def recognize_intent(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""识别 ai 与人类意图 将工作流注入新一条 HumanMessage"""
	
	config = store_recall(PLUGIN_CONFIG)
	
	messages = state.get("messages", [])
	if not messages:
		return None
	
	# 只拿 ai/human 信息
	if not isinstance(messages[-1], (AIMessage, HumanMessage)):
		return None
	
	content		= content_to_text(messages[-1])
	segments	= {}
	
	for workflow in config.workflows:
		
		# 需要全部命中
		hited = all([rule.is_hit(content)
			for rule in workflow.rules])
		
		if not hited:
			continue
		
		segments[workflow.name] = workflow.content
	
	# 没有 segments 则跳过注入
	if not segments:
		return None
	
	# 组装信息
	text = build_prompt(segments) # 构造字段与工作流的信息
	text = GUIDE + "\n" + text # 加入导句
	text = f"<{TAG}>\n" + text + f"\n</{TAG}>" # 转为格式化信息

	return {"messages": [HumanMessage(text)]}