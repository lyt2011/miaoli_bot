from miaoli_bot.core	import PluginProtocol
from miaoli_bot.api		import get_handler_registry
from miaoli_bot.consts	import MINIMUM, ON_AGENT_START, ON_TURN_START, ON_BEFORE_COMPACT, ON_COMPACT, ON_AFTER_COMPACT, ON_BEFORE_REQUEST, ON_REQUEST, ON_AFTER_REQUEST, ON_TOOL_CALLING, ON_TURN_END, ON_AGENT_END

from .models	import PluginConfig
from .nodes		import (
	on_agent_start,
	on_turn_start,
	on_before_compact,
	on_compact,
	on_after_compact,
	on_before_request,
	on_request,
	on_after_request,
	on_tool_calling,
	on_turn_end,
	on_agent_end,
)

class DefaultRouting(PluginProtocol):
	
	"""
	默认跳转
	
	给每个事件挂一个默认跳转 图才有了顺序
	注册在 MINIMUM(最低优先级) 因为优先级大的先跑 且 Goto 会短路本事件剩余处理器
	于是别的插件只要挂在更高优先级上 就能抢在默认跳转之前改道或叫停
	"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		registry = get_handler_registry()
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		self.undo_list.append(registry.on(ON_AGENT_START, on_agent_start, priority=MINIMUM))
		self.undo_list.append(registry.on(ON_TURN_START, on_turn_start, priority=MINIMUM))
		self.undo_list.append(registry.on(ON_BEFORE_COMPACT, on_before_compact, priority=MINIMUM))
		self.undo_list.append(registry.on(ON_COMPACT, on_compact, priority=MINIMUM))
		self.undo_list.append(registry.on(ON_AFTER_COMPACT, on_after_compact, priority=MINIMUM))
		self.undo_list.append(registry.on(ON_BEFORE_REQUEST, on_before_request, priority=MINIMUM))
		self.undo_list.append(registry.on(ON_REQUEST, on_request, priority=MINIMUM))
		self.undo_list.append(registry.on(ON_AFTER_REQUEST, on_after_request, priority=MINIMUM))
		self.undo_list.append(registry.on(ON_TOOL_CALLING, on_tool_calling, priority=MINIMUM))
		self.undo_list.append(registry.on(ON_TURN_END, on_turn_end, priority=MINIMUM))
		self.undo_list.append(registry.on(ON_AGENT_END, on_agent_end, priority=MINIMUM))
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
