from miaoli_bot.api			import get_handler_registry
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

from .nodes	import build_prompt


class PromptBuilder(PluginProtocol):
	
	"""把 state 里的提示词段拼成一条系统消息，插到消息列表最前面"""
	
	async def on_load(self) -> None:
		
		registry = get_handler_registry()
		
		registry.on_before_request(build_prompt, priority=NORMAL + 1)
	
	async def on_close(self) -> None:
		
		registry = get_handler_registry()
		
		registry.remove_before_request(build_prompt)
