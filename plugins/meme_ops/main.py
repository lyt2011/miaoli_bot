from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import NORMAL, ON_AGENT_START
from miaoli_bot.api		import store_drop, store_set, register_tool, get_handler_registry

from .models	import PluginConfig
from .nodes		import inject_doc, inject_memes
from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .tools		import (
	archive_meme,
	send_meme_to_qq,
	remove_meme_by_hash,
)


class MemeOps(PluginProtocol):
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		plugin_config	= PluginConfig.model_validate(self.config)
		
		store_set(RAW_CONFIG, self.config)
		store_set(PLUGIN_CONFIG, plugin_config)
	
		handler_registry	= get_handler_registry()
		self.undo_list		= []
		
		# 关闭时不注册任何工具与节点
		if not plugin_config.enable:
			return
		
		self.undo_list.append(register_tool(archive_meme))
		self.undo_list.append(register_tool(send_meme_to_qq))
		self.undo_list.append(register_tool(remove_meme_by_hash))
		
		self.undo_list.append(handler_registry.on(ON_AGENT_START, inject_doc, priority=NORMAL))
		self.undo_list.append(handler_registry.on(ON_AGENT_START, inject_memes, priority=NORMAL))

	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
		
		store_drop(RAW_CONFIG)
		store_drop(PLUGIN_CONFIG)
