from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import MEDIUM, ON_REQUEST
from miaoli_bot.api		import get_handler_registry

from .nodes	import fix_pending_tool_call


class PendingToolFixer(PluginProtocol):
	
	"""修复悬空工具调用"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		registry = get_handler_registry()
		
		# 优先级高于 call_llm(0) 保证在请求模型之前修好
		self.undo_list.append(registry.on(ON_REQUEST, fix_pending_tool_call, priority=MEDIUM))
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
