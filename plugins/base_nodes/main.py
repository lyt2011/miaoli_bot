from miaoli_bot.api			import get_handler_registry
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

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
		
		registry.on_turn_start(build_client, priority=NORMAL)
		registry.on_request(call_llm, priority=NORMAL)
		registry.on_tool_call(invoke_tools, priority=NORMAL)
		registry.on_agent_end(output_checker, priority=NORMAL+1)
		registry.on_agent_end(latest_to_answer, priority=NORMAL)

	async def on_close(self) -> None:
		
		registry = get_handler_registry()
		
		registry.remove_turn_start(build_client)
		registry.remove_request(call_llm)
		registry.remove_tool_call(invoke_tools)
		registry.remove_agent_end(output_checker)
		registry.remove_agent_end(latest_to_answer)
