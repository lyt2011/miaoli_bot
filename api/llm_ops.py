from ..core		import SHARE_STORE
from ..consts	import PLUGIN_CONFIG
from ..models	import LLM, Provider
from ..errors	import ModelNotFound, ProviderNotFound


def get_model_info() -> LLM:
	
	"""获取当前使用的模型对象 找不到就抛 ModelNotFound"""
	
	config		= SHARE_STORE.recall(PLUGIN_CONFIG)
	provider	= get_provider_info()
	
	mapping	= {md.name: md for md in provider.models}
	model	= mapping.get(config.llm.model, None)
	
	if model is None:
		raise ModelNotFound(f"供应商 '{provider.name}' 未配置 '{config.llm.model}' 模型")
	
	return model

def get_provider_info() -> Provider:
	
	"""获取当前使用的供应商对象 找不到就抛 ProviderNotFound"""
	
	config = SHARE_STORE.recall(PLUGIN_CONFIG)
	
	mapping		= {pv.name: pv for pv in config.llm.providers}
	provider	= mapping.get(config.llm.provider, None)
	
	if provider is None:
		raise ProviderNotFound(f"供应商 '{config.llm.provider}' 未配置")
	
	return provider
