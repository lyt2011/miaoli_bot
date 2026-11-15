from base_llm.api	import build_client as build_llm

from langgraph.runtime	import Runtime

from miaoli_bot.api		import get_root_config
from miaoli_bot.models	import GraphRuntimeContext, GraphState


async def build_client(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> None:
	
	"""通过配置构建 client 实例"""
	
	# 先拿配置
	config = get_root_config()
	
	# 再构建实例
	runtime.context["client"]	= build_llm(config.llm.provider, config.llm.model)
