from langgraph.runtime	import Runtime

from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing	import Dict, Any

import logging


LOGGER = logging.getLogger("CallLLM")


async def call_llm(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:

	"""
	请求模型并追加回复
	压缩后的摘要已由 context_compactor 写进 messages，这里无需再拼
	"""
	
	tools		= runtime.context["tool_surface"].tools
	client		= runtime.context["client"].bind_tools(tools)
	assistant	= await client.ainvoke(state["messages"])
	
	usage			= assistant.usage_metadata or {}
	details			= usage.get("input_token_details") or {}
	input_tokens	= usage.get("input_tokens") or 0
	cache_read		= details.get("cache_read") or 0
	output_tokens	= usage.get("output_tokens") or 0
	
	LOGGER.info(
		f"token 用量 输入={input_tokens} 命中缓存={cache_read} 未命中={input_tokens - cache_read} "
		f"输出={output_tokens} 消息数={len(state["messages"])} 工具数={len(tools)}"
	)

	return {"messages": [assistant]}
