from miaoli_bot.api			import get_tool_registry
from miaoli_bot.protocols	import PluginProtocol

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
		
		tool_registry = get_tool_registry()
		
		tool_registry.register(send_file_to_qq)
		tool_registry.register(download_qq_file)
		tool_registry.register(send_message_to_qq)
		tool_registry.register(delete_qq_message)
		tool_registry.register(query_qq_message_id)
		tool_registry.register(send_poke)
	
	async def on_close(self) -> None:
		
		tool_registry = get_tool_registry()
		
		tool_registry.remove(send_file_to_qq.name, ignore_error=True)
		tool_registry.remove(download_qq_file.name, ignore_error=True)
		tool_registry.remove(send_message_to_qq.name, ignore_error=True)
		tool_registry.remove(delete_qq_message.name, ignore_error=True)
		tool_registry.remove(query_qq_message_id.name, ignore_error=True)
		tool_registry.remove(send_poke.name, ignore_error=True)
