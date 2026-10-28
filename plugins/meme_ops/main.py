from miaoli_bot.api			import store_drop, store_set, get_handler_registry, get_tool_registry
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

from .models	import PluginConfig
from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .nodes		import inject_doc, inject_memes
from .tools		import (
	archive_meme,
	send_meme_to_qq,
	remove_meme_by_hash,
)


class MemeOps(PluginProtocol):
	
	async def on_load(self) -> None:
		
		plugin_config	= PluginConfig.model_validate(self.config)
		
		store_set(RAW_CONFIG, self.config)
		store_set(PLUGIN_CONFIG, plugin_config)
	
		handler_registry	= get_handler_registry()
		tool_registry		= get_tool_registry()
		
		# 关闭时不注册任何工具与节点
		if not plugin_config.enable:
			return
		
		tool_registry.register(archive_meme)
		tool_registry.register(send_meme_to_qq)
		tool_registry.register(remove_meme_by_hash)
		
		handler_registry.on_agent_start(inject_doc, priority=NORMAL)
		handler_registry.on_agent_start(inject_memes, priority=NORMAL)

	async def on_close(self) -> None:
		
		handler_registry	= get_handler_registry()
		tool_registry		= get_tool_registry()
		
		tool_registry.remove(archive_meme.name, ignore_error=True)
		tool_registry.remove(send_meme_to_qq.name, ignore_error=True)
		tool_registry.remove(remove_meme_by_hash.name, ignore_error=True)
		
		handler_registry.remove_agent_start(inject_doc)
		handler_registry.remove_agent_start(inject_memes)
		
		store_drop(RAW_CONFIG)
		store_drop(PLUGIN_CONFIG)
