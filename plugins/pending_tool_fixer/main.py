from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import MEDIUM, ON_REQUEST
from miaoli_bot.api		import store_set, get_handler_registry

from .models	import PluginConfig
from .nodes		import fix_pending_tool_call
from .consts	import PLUGIN_CONFIG, RAW_CONFIG


class PendingToolFixer(PluginProtocol):
	
	"""修复悬空工具调用"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		registry = get_handler_registry()
		
		
		self.undo_list.append(store_set(PLUGIN_CONFIG, config))
		self.undo_list.append(store_set(RAW_CONFIG, self.config))
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		# 优先级高于 call_llm(0) 保证在请求模型之前修好
		self.undo_list.append(registry.on(ON_REQUEST, fix_pending_tool_call, priority=MEDIUM))
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
