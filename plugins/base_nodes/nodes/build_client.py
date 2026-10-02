from miaoli_bot			import GraphRuntimeContext, GraphState, SHARE_STORE
from miaoli_bot.consts	import PLUGIN_CONFIG
from typing				import Dict, Any

from langgraph.runtime	import Runtime
from langchain_openai	import ChatOpenAI


async def build_client(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""通过配置构建 client 实例"""
	
	root_config	= SHARE_STORE.recall(PLUGIN_CONFIG)
	
	provider_name	= state["provider_name"]
	model_name		= state["model_name"]
	
	provider	= root_config.providers[provider_name]
	model		= provider.models[model_name]
	
	runtime.context["client"]	= ChatOpenAI(
		model		= model_name,
		base_url	= provider.base_url,
		api_key		= provider.api_key,
		max_tokens	= model.max_tokens,
	)
	
	return {}