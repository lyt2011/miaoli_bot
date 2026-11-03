from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import NORMAL, ON_BEFORE_COMPACT, ON_COMPACT
from miaoli_bot.api		import store_drop, store_set, get_handler_registry

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
		
		self.undo_list = []  # 关闭时 on_close 也要能遍历
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		self.undo_list = [
			registry.on(ON_BEFORE_COMPACT, should_compact, priority=NORMAL),
			registry.on(ON_COMPACT, compact, priority=NORMAL),
		]
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
		
		store_drop(PLUGIN_CONFIG)
		store_drop(RAW_CONFIG)
