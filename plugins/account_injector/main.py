from miaoli_bot.core	import PluginProtocol
from miaoli_bot.api		import get_handler_registry
from miaoli_bot.consts	import NORMAL, ON_AGENT_START

from .nodes	import inject_account


class AccountInjector(PluginProtocol):
	
	"""提供账号注入"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		registry = get_handler_registry()
		
		self.undo_list = [
			registry.on(ON_AGENT_START, inject_account, priority=NORMAL),
		]

	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
