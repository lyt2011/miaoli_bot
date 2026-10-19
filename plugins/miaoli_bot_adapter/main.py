from miaoli_bot.api			import store_drop, store_set
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .models	import PluginConfig
from .nodes		import inject_model_info, inject_soul


class MiaoliBotAdapter(PluginProtocol):
	
	"""把 miaoli_bot 的内部数据适配成图节点可直接消费的形状"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		store_set(RAW_CONFIG, self.config)
		store_set(PLUGIN_CONFIG, config)
		
		# 不启用直接跳过节点与工具注册
		if not config.enable:
			return None
		
		# 必须先于 build_client 写入 base_url / api_key / model / max_tokens
		self.registry.on_turn_start(inject_model_info, priority=NORMAL + 1)
		self.registry.on_turn_start(inject_soul, priority=NORMAL + 1)
	
	async def on_close(self) -> None:
		
		store_drop(RAW_CONFIG)
		store_drop(PLUGIN_CONFIG)
