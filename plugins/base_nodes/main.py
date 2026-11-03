from miaoli_bot.core	import PluginProtocol
from miaoli_bot.api		import get_handler_registry
from miaoli_bot.consts	import NORMAL, ON_TURN_START, ON_REQUEST, ON_TOOL_CALLING, ON_AGENT_END

from .nodes	import (
	call_llm,
	invoke_tools,
	latest_to_answer,
	build_client,
	output_checker,
)


class BaseNodes(PluginProtocol):
	
	"""基础节点 保证图运作正常"""

	async def on_load(self) -> None:
		
		registry = get_handler_registry()
		
		self.undo_list = [
			registry.on(ON_TURN_START, build_client, priority=NORMAL),
			registry.on(ON_REQUEST, call_llm, priority=NORMAL),
			registry.on(ON_TOOL_CALLING, invoke_tools, priority=NORMAL),
			registry.on(ON_AGENT_END, output_checker, priority=NORMAL+1),
			registry.on(ON_AGENT_END, latest_to_answer, priority=NORMAL),
		]

	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
