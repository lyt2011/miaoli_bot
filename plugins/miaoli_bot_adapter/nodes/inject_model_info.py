from miaoli_bot.api		import get_model_info, get_provider_info
from miaoli_bot.models	import GraphRuntimeContext, GraphState
from typing				import Any, Dict

from langgraph.runtime	import Runtime


async def inject_model_info(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""注入模型信息 给 build_client 构造 [OI] 实例"""
	
	# 获取模型与供应商信息
	provider_info	: Dict[str, Any] = get_provider_info()
	model_info		: Dict[str, Any] = get_model_info()
	
	# 短名配置
	base_url	= provider_info["base_url"]
	api_key		= provider_info["api_key"]
	model		= model_info["name"]
	max_tokens	= model_info["max_tokens"]
	
	return {"base_url": base_url, "api_key": api_key, "model": model, "max_tokens": max_tokens}
