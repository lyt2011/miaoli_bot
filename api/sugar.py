from typing	import Any, Dict

from ..consts	import PLUGIN_CONFIG
from ..stores	import SHARE_STORE


def get_model_info() -> Dict[str, Any]:
	
	"""便捷的模型信息获取 api 使用当前配置模型拿信息"""
	
	plugin_cfg = SHARE_STORE.recall(PLUGIN_CONFIG)
	
	provider_name	= plugin_cfg.provider
	model_name		= plugin_cfg.model
	
	# 链式获取模型信息
	model_info = (
		plugin_cfg.providers
		.get(provider_name, {})
		.models.get(model_name)
	)
	
	# 这是主包配置问题 应该报错而不是 return None
	if model_info is None:
		raise RuntimeError("无法获取模型信息")
	
	return model_info.model_dump()

def get_prompt() -> str:
	"""获取提示词的便捷 api"""
	return SHARE_STORE.recall(PLUGIN_CONFIG).prompt
