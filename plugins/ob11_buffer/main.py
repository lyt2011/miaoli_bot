from miaoli_bot.api		import register_tool
from miaoli_bot.core	import PluginProtocol

from .tools	import get_qq_unread_messages


class OB11BufferTools(PluginProtocol):
	
	"""把缓冲区里的未读消息交给模型读取"""
	
	async def on_load(self) -> None:
		
		self.undo_list = [
			register_tool(get_qq_unread_messages),
		]
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
