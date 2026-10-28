from miaoli_bot.api			import store_drop, store_set, get_tool_registry
from miaoli_bot.protocols	import PluginProtocol

from .tools		import write, replace, read_image, read_file, bash
from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .models	import PluginConfig


class BaseSystemTools(PluginProtocol):
	
	"""基础系统工具"""

	async def on_load(self) -> None:
		
		tool_registry = get_tool_registry()
		
		store_set(RAW_CONFIG, self.config)
		store_set(PLUGIN_CONFIG, PluginConfig.model_validate(self.config))

		tool_registry.register(write)
		tool_registry.register(replace)
		tool_registry.register(read_image)
		tool_registry.register(read_file)
		tool_registry.register(bash)
	
	async def on_close(self) -> None:
		
		tool_registry = get_tool_registry()
		
		tool_registry.remove(write.name, ignore_error=True)
		tool_registry.remove(replace.name, ignore_error=True)
		tool_registry.remove(read_image.name, ignore_error=True)
		tool_registry.remove(read_file.name, ignore_error=True)
		tool_registry.remove(bash.name, ignore_error=True)
		
		store_drop(RAW_CONFIG)
		store_drop(PLUGIN_CONFIG)
