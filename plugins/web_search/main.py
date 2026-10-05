from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.stores		import SHARE_STORE

import aiohttp

from .consts	import PLUGIN_CONFIG, RAW_CONFIG, CLIENT_SESSION
from .models	import PluginConfig
from .tools		import lang_search


class WebSearch(PluginProtocol):
	
	"""联网搜索工具"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		SHARE_STORE.set(PLUGIN_CONFIG, config)
		SHARE_STORE.set(RAW_CONFIG, self.config)
		SHARE_STORE.set(CLIENT_SESSION, aiohttp.ClientSession())
		
		# 不启用直接跳过工具注册
		if not config.enable:
			return None
		
		# 根据实际需求注册工具
		if config.provider == "langsearch":
			self.registry.register_tool(lang_search)
	
	async def on_close(self) -> None:
		
		client_session = SHARE_STORE.recall(CLIENT_SESSION)
		
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
		SHARE_STORE.drop(CLIENT_SESSION)
		
		# 丢完再关闭 防止中途报错导致键残留
		await client_session.close()