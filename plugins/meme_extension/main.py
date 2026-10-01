from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot				import SHARE_STORE

from .models	import PluginConfig
from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .tools		import (
	list_memes,
	archive_meme,
	send_meme_to_qq,
	remove_meme_by_hash,
	search_memes_by_tags,
)


class MemeExtension(PluginProtocol):
	
	async def on_load(self) -> None:
		
		SHARE_STORE.set(RAW_CONFIG, self.config)
		SHARE_STORE.set(PLUGIN_CONFIG, PluginConfig.model_validate(self.config))
		
		self.registry.register_tool(archive_meme)
		self.registry.register_tool(send_meme_to_qq)
		self.registry.register_tool(list_memes)
		self.registry.register_tool(remove_meme_by_hash)
		self.registry.register_tool(search_memes_by_tags)

	async def on_close(self) -> None:
		
		SHARE_STORE.drop(RAW_CONFIG)
		SHARE_STORE.drop(PLUGIN_CONFIG)
