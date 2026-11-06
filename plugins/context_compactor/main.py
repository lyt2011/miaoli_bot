from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import NORMAL, ON_BEFORE_COMPACT, ON_COMPACT
from miaoli_bot.api		import store_set, get_handler_registry

from .models	import PluginConfig
from .nodes		import compact, should_compact
from .consts	import PLUGIN_CONFIG, RAW_CONFIG


class ContextCompactor(PluginProtocol):
	
	"""上下文压缩"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		registry = get_handler_registry()
		
		self.undo_list.append(store_set(PLUGIN_CONFIG, config))
		self.undo_list.append(store_set(RAW_CONFIG, self.config))
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		self.undo_list.append(registry.on(ON_BEFORE_COMPACT, should_compact, priority=NORMAL))
		self.undo_list.append(registry.on(ON_COMPACT, compact, priority=NORMAL))
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
