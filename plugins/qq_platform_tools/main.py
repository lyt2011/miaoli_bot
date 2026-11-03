from miaoli_bot.api		import register_tool
from miaoli_bot.core	import PluginProtocol

from .tools	import (
	send_file_to_qq,
	download_qq_file,
	send_message_to_qq,
	delete_qq_message,
	query_qq_message_id,
	send_poke,
)


class QQPlatformTools(PluginProtocol):
	
	"""QQ 平台工具"""
	
	async def on_load(self) -> None:
		
		self.undo_list = [
			register_tool(send_file_to_qq),
			register_tool(download_qq_file),
			register_tool(send_message_to_qq),
			register_tool(delete_qq_message),
			register_tool(query_qq_message_id),
			register_tool(send_poke),
		]
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
