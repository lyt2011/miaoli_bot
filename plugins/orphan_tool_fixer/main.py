from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import NORMAL, ON_REQUEST
from miaoli_bot.api		import get_handler_registry

from .models	import PluginConfig
from .nodes		import fix_orphan_tool_message

class OrphanToolFixer(PluginProtocol):
	
	"""修复孤儿工具返回"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		registry = get_handler_registry()
		
		self.undo_list = []  # 关闭时 on_close 也要能遍历
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		self.undo_list = [
			registry.on(ON_REQUEST, fix_orphan_tool_message, priority=NORMAL+2),
		]
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
