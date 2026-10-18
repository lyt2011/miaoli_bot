from typing	import Any, Dict

from ..consts	import PLUGIN_CONFIG
from ..models	import LLM, Provider
from ..stores	import SHARE_STORE


def get_model_info() -> Dict[str, Any]:
	
	"""便捷的模型信息获取 api 使用当前配置模型拿信息"""
	
	plugin_cfg = SHARE_STORE.recall(PLUGIN_CONFIG)
	
	provider_name	= plugin_cfg.provider
	model_name		= plugin_cfg.model
	
	# 获取供应商列表
	providers: Dict[str, Provider] = {p.name: p for p in plugin_cfg.providers}
	if provider_name not in providers:
		raise KeyError(f"供应商 '{provider_name}' 未配置")
	
	# 获取模型列表
	models: Dict[str, LLM] = {model.name: model for model in providers[provider_name].models}
	if model_name not in models:
		raise KeyError(f"供应商 '{provider_name}' 未配置 '{model_name}' 模型")
	
	return models[model_name].model_dump()

def get_provider_info() -> Dict[str, Any]:
	
	"""获取供应商信息"""
	
	plugin_cfg = SHARE_STORE.recall(PLUGIN_CONFIG)
	
	provider_name = plugin_cfg.provider
	
	# 获取供应商列表
	providers: Dict[str, Provider] = {p.name: p for p in plugin_cfg.providers}
	if provider_name not in providers:
		raise KeyError(f"供应商 '{provider_name}' 未配置")
	
	return providers[provider_name].model_dump()

def get_prompt() -> str:
	"""获取提示词的便捷 api"""
	return SHARE_STORE.recall(PLUGIN_CONFIG).prompt
