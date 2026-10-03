from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import MINIMUM

from .models	import PluginConfig
from .nodes		import (
	on_agent_start,
	on_turn_start,
	on_before_request,
	on_request,
	on_after_request,
	on_tool_calling,
	on_turn_end,
	on_agent_end,
)

class NodeConnectionFix(PluginProtocol):
	
	"""
	节点连接修复
	
	给每个事件挂一个默认跳转 图才有了顺序
	注册在 MINIMUM(最低优先级) 因为优先级大的先跑 且 Goto 会短路本事件剩余处理器
	于是别的插件只要挂在更高优先级上 就能抢在默认跳转之前改道或叫停
	"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		self.registry.on_agent_start(on_agent_start, priority=MINIMUM)
		self.registry.on_turn_start(on_turn_start, priority=MINIMUM)
		self.registry.on_before_request(on_before_request, priority=MINIMUM)
		self.registry.on_request(on_request, priority=MINIMUM)
		self.registry.on_after_request(on_after_request, priority=MINIMUM)
		self.registry.on_tool_call(on_tool_calling, priority=MINIMUM)
		self.registry.on_turn_end(on_turn_end, priority=MINIMUM)
		self.registry.on_agent_end(on_agent_end, priority=MINIMUM)
	
	async def on_close(self) -> None: ...
