from miaoli_bot.protocols	import PluginProtocol

from .file_ops		import (
	send_file_to_qq,
	download_qq_file,
)
from .message_ops	import (
	send_message_to_qq,
	delete_qq_message,
	query_qq_message_id,
)


class BasePlatformTools(PluginProtocol):
	
	"""基础平台工具"""

	async def on_load(self) -> None:

		self.registry.register_tool(send_file_to_qq)
		self.registry.register_tool(download_qq_file)
		self.registry.register_tool(send_message_to_qq)
		self.registry.register_tool(delete_qq_message)
		self.registry.register_tool(query_qq_message_id)

	async def on_close(self) -> None: ...