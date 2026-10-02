from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.core		import Registry
from miaoli_bot.consts		import DEFAULT_PRIORITY

from typing				import Any, Dict

from .nodes	import (
	format_input,
	compact,
	call_llm,
	invoke_tools,
	attach_image,
	latest_to_answer,
	build_client,
)


class BaseNodes(PluginProtocol):
	
	"""基础节点 保证图运作正常"""

	def __init__(self, config: Dict[str, Any], registry: Registry) -> None:
		super().__init__(config, registry)

	async def on_load(self) -> None:

		self.registry.on_agent_start(format_input, priority=DEFAULT_PRIORITY)
		self.registry.on_turn_start(build_client, priority=DEFAULT_PRIORITY)
		self.registry.on_request(compact, priority=DEFAULT_PRIORITY+1)
		self.registry.on_request(call_llm, priority=DEFAULT_PRIORITY)
		self.registry.on_tool_call(invoke_tools, priority=DEFAULT_PRIORITY)
		self.registry.on_tool_call(attach_image, priority=DEFAULT_PRIORITY-1)
		self.registry.on_agent_end(latest_to_answer, priority=DEFAULT_PRIORITY)

	async def on_close(self) -> None: ...