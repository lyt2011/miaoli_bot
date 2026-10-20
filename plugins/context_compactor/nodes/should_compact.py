from miaoli_bot.api		import get_model_info, store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState
from miaoli_bot.consts	import ON_COMPACT, ON_BEFORE_REQUEST

from miaoli_pipeline.actions	import Goto

from typing				import Any
from langgraph.runtime	import Runtime

from ..consts	import PLUGIN_CONFIG
from ..utils	import base_calculate, tiktoken_calculate

import tiktoken


async def should_compact(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Any:
	
	"""压缩守卫 —— 需要压缩就跳 on_compact 否则跳 on_before_request"""
	
	plugin_cfg = store_recall(PLUGIN_CONFIG)
	
	messages = state.get("messages", [])
	
	# 根据计算模式动态选择公式/tiktoken
	if plugin_cfg.calculate.mode == "base":
		usage_tokens = base_calculate(messages)
	
	elif plugin_cfg.calculate.mode == "tiktoken":
		encoding		= tiktoken.get_encoding(plugin_cfg.calculate.encoder)
		usage_tokens	= tiktoken_calculate(messages, encoding=encoding)
	
	else:
		raise RuntimeError(f"未知的模式: {plugin_cfg.calculate.mode}")
	
	model_info = get_model_info()
	
	# 保证有压缩余量
	if (usage_tokens + model_info["max_tokens"]) < model_info["context_window"]:
		return Goto(goto=ON_BEFORE_REQUEST)
	
	return Goto(goto=ON_COMPACT)
