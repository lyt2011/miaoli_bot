from miaoli_bot.api			import store_drop, store_set
from miaoli_bot.protocols	import PluginProtocol

from .tools		import write, replace, read_image, read_file, bash
from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .models	import PluginConfig


class BaseSystemTools(PluginProtocol):
	
	"""基础系统工具"""

	async def on_load(self) -> None:
		
		store_set(RAW_CONFIG, self.config) # 注意这个不会自动通过默认值补全
		store_set(PLUGIN_CONFIG, PluginConfig.model_validate(self.config))

		self.registry.register_tool(write)
		self.registry.register_tool(replace)
		self.registry.register_tool(read_image)
		self.registry.register_tool(read_file)
		self.registry.register_tool(bash)
	
	async def on_close(self) -> None:
		
		store_drop(RAW_CONFIG)
		store_drop(PLUGIN_CONFIG)
