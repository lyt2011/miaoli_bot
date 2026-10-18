
from miaoli_bot.api	import store_recall
from ..consts		import PLUGIN_CONFIG


def is_target_model(provider: str, model: str) -> bool:
	
	"""适配 <provider>/<model>与<model>"""
	
	plugin_config	= store_recall(PLUGIN_CONFIG)
	
	if not plugin_config.models:
		return True
	
	pm_hit	= f"{provider}/{model}" in plugin_config.models
	m_hit	= f"{model}" in plugin_config.models
	
	return pm_hit or m_hit
