from miaoli_bot.api			import store_drop, store_set
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

from .models	import PluginConfig
from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .nodes		import inject_helper
from .tools		import (
	list_memes,
	archive_meme,
	send_meme_to_qq,
	remove_meme_by_hash,
	search_memes_by_tags,
)


class MemeOps(PluginProtocol):
	
	async def on_load(self) -> None:
	
		plugin_config = PluginConfig.model_validate(self.config)
		
		store_set(RAW_CONFIG, self.config)
		store_set(PLUGIN_CONFIG, plugin_config)
		
		# 关闭时不注册任何工具与节点
		if not plugin_config.enable:
			return
		
		self.registry.register_tool(archive_meme)
		self.registry.register_tool(send_meme_to_qq)
		self.registry.register_tool(list_memes)
		self.registry.register_tool(remove_meme_by_hash)
		self.registry.register_tool(search_memes_by_tags)
		
		self.registry.on_agent_start(inject_helper, priority=NORMAL)

	async def on_close(self) -> None:
		
		store_drop(RAW_CONFIG)
		store_drop(PLUGIN_CONFIG)
