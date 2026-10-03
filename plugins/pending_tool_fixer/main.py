from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.stores		import SHARE_STORE
from miaoli_bot.consts		import DEFAULT_PRIORITY

from .models	import PluginConfig
from .nodes		import fix_pending_tool_call
from .consts	import PLUGIN_CONFIG, RAW_CONFIG


class PendingToolFixer(PluginProtocol):
	
	"""修复悬空工具调用"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		SHARE_STORE.set(PLUGIN_CONFIG, config)
		SHARE_STORE.set(RAW_CONFIG, self.config)
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		# 优先级高于 compact(1) 与 call_llm(0) 保证在请求模型之前修好
		self.registry.on_before_request(fix_pending_tool_call, priority=DEFAULT_PRIORITY+3)
	
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
