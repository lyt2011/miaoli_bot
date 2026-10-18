from miaoli_bot.api		import get_model_info, store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing						import Any, Dict, Optional
from langgraph.runtime			import Runtime
from langgraph.types			import Overwrite
from langchain_core.messages	import HumanMessage, SystemMessage

from ..consts	import PLUGIN_CONFIG
from ..utils	import base_calculate, keep_recent_messages, tiktoken_calculate

import tiktoken	


async def compact(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""上下文压缩节点"""
	
	s_plugin_config	= store_recall(PLUGIN_CONFIG)
	
	messages	= state["messages"]
	
	# 根据计算模式动态选择公式/tiktoken
	if s_plugin_config.calculate.mode == "base":
		usage_tokens = base_calculate(messages)
	
	elif s_plugin_config.calculate.mode == "tiktoken":
		encoding		= tiktoken.get_encoding(s_plugin_config.calculate.encoder)
		usage_tokens	= tiktoken_calculate(messages, encoding=encoding)
	
	else: raise RuntimeError(f"未知的模式: {s_plugin_config.calculate.mode}")
	
	model_info		= get_model_info()
	
	# 保证有压缩余量
	if (usage_tokens + model_info["max_tokens"]) < model_info["context_window"]:
		return None
	
	# 构建压缩请求上下文并根据实际需求插入系统提示词
	compact_ctx	= [*messages, HumanMessage(s_plugin_config.prompt)]
	if (sprompt := state.get("system_prompt")):
		compact_ctx.insert(0, SystemMessage(sprompt))
	
	# 通过大模型压缩上下文 保留有效信
	ai_message	= await runtime.context["client"].ainvoke(compact_ctx)
	kp_messages	= keep_recent_messages(messages, n=s_plugin_config.keep_count)
	compaction	= HumanMessage(f"<compaction>{ai_message.content}</compaction>")
	
	# 覆盖messages
	return {"messages": Overwrite([compaction, *kp_messages])}
