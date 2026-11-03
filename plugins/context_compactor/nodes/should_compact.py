from langchain_core.messages	import HumanMessage

from langgraph.runtime	import Runtime

from miaoli_bot.core	import Goto
from miaoli_bot.api		import get_model_info, store_recall
from miaoli_bot.consts	import ON_COMPACT, ON_BEFORE_REQUEST
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts	import PLUGIN_CONFIG
from ..utils	import base_calculate, tiktoken_calculate, read_compact_prompt

from typing	import Any

import logging
import tiktoken


LOGGER = logging.getLogger("ContextCompactor")


async def should_compact(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Any:
	
	"""压缩守卫 —— 需要压缩就跳 on_compact 否则跳 on_before_request"""
	
	plugin_cfg = store_recall(PLUGIN_CONFIG)
	
	messages	= state.get("messages", [])
	messages	= [*messages, HumanMessage(read_compact_prompt())] # 加一条压缩提示词进去
	
	# 根据计算模式动态选择公式/tiktoken
	if plugin_cfg.calculate.mode == "base":
		usage_tokens = base_calculate(messages)
	
	elif plugin_cfg.calculate.mode == "tiktoken":
		encoding		= tiktoken.get_encoding(plugin_cfg.calculate.encoder)
		usage_tokens	= tiktoken_calculate(messages, encoding=encoding)
	
	else:
		raise RuntimeError(f"未知的模式: {plugin_cfg.calculate.mode}")
	
	model_info = get_model_info()
	threshold  = model_info["context_window"] - model_info["max_tokens"]
	
	LOGGER.info(
		f"守卫 估算={usage_tokens} 阈值={threshold} "
		f"窗口={model_info['context_window']} 预留={model_info['max_tokens']} 消息数={len(messages)}"
	)
	
	# 保证有压缩余量
	if (usage_tokens + model_info["max_tokens"]) < model_info["context_window"]:
		LOGGER.info("守卫 判定=不压缩")
		return Goto(goto=ON_BEFORE_REQUEST)
	
	LOGGER.info("守卫 判定=压缩")
	return Goto(goto=ON_COMPACT)
