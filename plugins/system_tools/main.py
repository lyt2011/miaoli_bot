from miaoli_bot.core	import PluginProtocol
from miaoli_bot.api		import store_set, register_tool

from .models	import PluginConfig
from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .tools		import write, replace, read_image, read_file, bash


class SystemTools(PluginProtocol):
	
	"""系统工具"""

	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		
		self.undo_list.append(store_set(RAW_CONFIG, self.config))
		self.undo_list.append(store_set(PLUGIN_CONFIG, PluginConfig.model_validate(self.config)))
		self.undo_list.append(register_tool(write))
		self.undo_list.append(register_tool(replace))
		self.undo_list.append(register_tool(read_image))
		self.undo_list.append(register_tool(read_file))
		self.undo_list.append(register_tool(bash))
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
