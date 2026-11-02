from ..core		import SHARE_STORE
from ..models	import PluginConfig
from ..consts	import PLUGIN_CONFIG


def get_root_config() -> PluginConfig:
	"""获取根配置 (miaoli_bot 的 config)"""
	return SHARE_STORE.recall(PLUGIN_CONFIG)
