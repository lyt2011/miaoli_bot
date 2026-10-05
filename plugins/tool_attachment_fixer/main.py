from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.stores		import SHARE_STORE
from miaoli_bot.consts		import NORMAL

from .models	import PluginConfig
from .nodes		import fix_tool_attachment
from .consts	import PLUGIN_CONFIG, RAW_CONFIG

class ToolAttachmentFixer(PluginProtocol):
	
	"""修复工具附件"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		SHARE_STORE.set(PLUGIN_CONFIG, config)
		SHARE_STORE.set(RAW_CONFIG, self.config)
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		self.registry.on_tool_call(fix_tool_attachment, priority=NORMAL-2)
	
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
