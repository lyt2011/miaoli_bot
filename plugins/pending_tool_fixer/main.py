from miaoli_bot.api			import store_drop, store_set
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

from .models	import PluginConfig
from .nodes		import fix_pending_tool_call
from .consts	import PLUGIN_CONFIG, RAW_CONFIG


class PendingToolFixer(PluginProtocol):
	
	"""修复悬空工具调用"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		store_set(PLUGIN_CONFIG, config)
		store_set(RAW_CONFIG, self.config)
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		# 优先级高于 call_llm(0) 保证在请求模型之前修好
		self.registry.on_request(fix_pending_tool_call, priority=NORMAL+2)
	
	async def on_close(self) -> None:
		
		store_drop(PLUGIN_CONFIG)
		store_drop(RAW_CONFIG)
