from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

from .models	import PluginConfig
from .nodes		import fix_orphan_tool_message

class OrphanToolFixer(PluginProtocol):
	
	"""修复孤儿工具返回"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		self.registry.on_before_request(fix_orphan_tool_message, priority=NORMAL+2)
	
	async def on_close(self) -> None: ...
