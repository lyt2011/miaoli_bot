from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot				import SHARE_STORE

from .tools		import write, replace, read_image, read_file, bash
from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .models	import PluginConfig


class BaseSystemTools(PluginProtocol):
	
	"""基础系统工具"""

	async def on_load(self) -> None:
		
		SHARE_STORE.set(RAW_CONFIG, self.config) # 注意这个不会自动通过默认值补全
		SHARE_STORE.set(PLUGIN_CONFIG, PluginConfig.model_validate(self.config))

		self.registry.register_tool(write)
		self.registry.register_tool(replace)
		self.registry.register_tool(read_image)
		self.registry.register_tool(read_file)
		self.registry.register_tool(bash)
	
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(RAW_CONFIG)
		SHARE_STORE.drop(PLUGIN_CONFIG)
