from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import NORMAL

from .nodes	import inject_account


class AccountInjector(PluginProtocol):
	
	"""提供账号注入"""
	
	async def on_load(self) -> None:
		
		self.registry.on_agent_start(inject_account, priority=NORMAL)

	async def on_close(self) -> None: ...