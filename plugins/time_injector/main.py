from miaoli_bot.core	import PluginProtocol
from miaoli_bot.api		import get_handler_registry, store_set
from miaoli_bot.consts	import MEDIUM, NORMAL, ON_AGENT_START, ON_BEFORE_REQUEST

from .models	import PluginConfig
from .nodes		import helper_inject, time_inject
from .consts	import LAST_INJECTED_AT, PLUGIN_CONFIG


class TimeInjector(PluginProtocol):
	
	"""按间隔注入时间信息"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		if config.enable:
			
			registry = get_handler_registry()
		
			self.undo_list.append(store_set(PLUGIN_CONFIG, config))
			self.undo_list.append(store_set(LAST_INJECTED_AT, {}))
			
			self.undo_list.append(registry.on(ON_BEFORE_REQUEST, time_inject, priority=MEDIUM))
			self.undo_list.append(registry.on(ON_AGENT_START, helper_inject, priority=NORMAL))
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
