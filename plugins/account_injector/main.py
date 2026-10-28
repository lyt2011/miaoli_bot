from miaoli_bot.api			import get_handler_registry
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

from .nodes	import inject_account


class AccountInjector(PluginProtocol):
	
	"""提供账号注入"""
	
	async def on_load(self) -> None:
		
		registry = get_handler_registry()
		
		registry.on_agent_start(inject_account, priority=NORMAL)

	async def on_close(self) -> None:
		
		registry = get_handler_registry()
		
		registry.remove_agent_start(inject_account)
