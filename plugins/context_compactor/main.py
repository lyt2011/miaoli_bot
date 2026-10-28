from miaoli_bot.api			import store_drop, store_set, get_handler_registry
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

from .models	import PluginConfig
from .nodes		import compact, should_compact
from .consts	import PLUGIN_CONFIG, RAW_CONFIG


class ContextCompactor(PluginProtocol):
	
	"""上下文压缩"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		registry = get_handler_registry()
		
		store_set(PLUGIN_CONFIG, config)
		store_set(RAW_CONFIG, self.config)
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		registry.on_before_compact(should_compact, priority=NORMAL)
		registry.on_compact(compact, priority=NORMAL)
	
	async def on_close(self) -> None:
		
		registry = get_handler_registry()
		
		registry.remove_before_compact(should_compact)
		registry.remove_compact(compact)
		
		store_drop(PLUGIN_CONFIG)
		store_drop(RAW_CONFIG)
