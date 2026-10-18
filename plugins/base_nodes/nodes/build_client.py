from miaoli_bot.models	import GraphRuntimeContext, GraphState

from langgraph.runtime	import Runtime
from langchain_openai	import ChatOpenAI


async def build_client(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> None:
	
	"""通过配置构建 client 实例"""
	
	base_url	= state["base_url"]
	api_key		= state["api_key"]
	model		= state["model"]
	max_tokens	= state["max_tokens"]
	
	client	= ChatOpenAI(
		model		= model,
		base_url	= base_url,
		api_key		= api_key,
		max_tokens	= max_tokens,
	)
	
	runtime.context["client"] = client