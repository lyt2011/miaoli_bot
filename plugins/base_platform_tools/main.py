from miaoli_bot.protocols	import PluginProtocol

from .tools		import (
	send_file_to_qq,
	download_qq_file,
	send_message_to_qq,
	delete_qq_message,
	query_qq_message_id,
	send_poke,
)


class BasePlatformTools(PluginProtocol):
	
	"""基础平台工具"""

	async def on_load(self) -> None:

		self.registry.register_tool(send_file_to_qq)
		self.registry.register_tool(download_qq_file)
		self.registry.register_tool(send_message_to_qq)
		self.registry.register_tool(delete_qq_message)
		self.registry.register_tool(query_qq_message_id)
		self.registry.register_tool(send_poke)

	async def on_close(self) -> None: ...