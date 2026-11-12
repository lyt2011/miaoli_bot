from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import LOW, ON_BEFORE_REQUEST
from miaoli_bot.api		import store_set, get_handler_registry

from .nodes		import pick_tools
from .models	import PluginConfig
from .consts	import PLUGIN_CONFIG, RAW_CONFIG


class ToolPermissionManager(PluginProtocol):
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		registry = get_handler_registry()
		
		
		self.undo_list.append(store_set(PLUGIN_CONFIG, config))
		self.undo_list.append(store_set(RAW_CONFIG, self.config))
				
		if not config.enable:
			return None
		
		self.undo_list.append(registry.on(ON_BEFORE_REQUEST, pick_tools, priority=LOW))
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
