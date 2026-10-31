from miaoli_bot.api			import get_handler_registry
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

from .nodes	import inject_current_time


class CurrentTimeInjector(PluginProtocol):
	
	"""每轮把当前时间注入 prompts.current_time"""
	
	async def on_load(self) -> None:
		
		registry = get_handler_registry()
		
		registry.on_turn_start(inject_current_time, priority=NORMAL + 1)
	
	async def on_close(self) -> None:
		
		registry = get_handler_registry()
		
		registry.remove_turn_start(inject_current_time)
