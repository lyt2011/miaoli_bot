from langgraph.runtime	import Runtime

from miaoli_bot.api		import build_client as build_llm
from miaoli_bot.models	import GraphRuntimeContext, GraphState


async def build_client(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> None:
	"""通过配置构建 client 实例"""
	runtime.context["client"] = build_llm()
