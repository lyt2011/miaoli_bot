from miaoli_bot.core	import PluginProtocol
from miaoli_bot.api		import store_drop, store_set, register_tool

from .models	import PluginConfig
from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .tools		import write, replace, read_image, read_file, bash


class SystemTools(PluginProtocol):
	
	"""系统工具"""

	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		store_set(RAW_CONFIG, self.config)
		store_set(PLUGIN_CONFIG, PluginConfig.model_validate(self.config))

		self.undo_list = [
			register_tool(write),
			register_tool(replace),
			register_tool(read_image),
			register_tool(read_file),
			register_tool(bash),
		]
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
		
		store_drop(RAW_CONFIG)
		store_drop(PLUGIN_CONFIG)
