from miaoli_bot.core	import PluginProtocol
from miaoli_bot.api		import get_handler_registry
from miaoli_bot.consts	import HIGH, NORMAL, LOWEST, ON_TURN_START, ON_BEFORE_REQUEST, ON_REQUEST, ON_TOOL_CALLING, ON_AGENT_END

from .nodes	import (
	compact_if_need,
	call_llm,
	invoke_tools,
	build_client,
	output_checker,
)


class BaseNodes(PluginProtocol):
	
	"""基础节点 保证图运作正常"""

	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		registry = get_handler_registry()
		
		self.undo_list.append(registry.on(ON_TURN_START, build_client, priority=NORMAL))
		self.undo_list.append(registry.on(ON_BEFORE_REQUEST, compact_if_need, priority=HIGH))
		self.undo_list.append(registry.on(ON_REQUEST, call_llm, priority=NORMAL))
		self.undo_list.append(registry.on(ON_TOOL_CALLING, invoke_tools, priority=NORMAL))
		self.undo_list.append(registry.on(ON_AGENT_END, output_checker, priority=LOWEST))

	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
