from miaoli_bot.core	import PluginProtocol


class BaseCompact(PluginProtocol):
	
	"""上下文压缩能力 只提供压缩逻辑不挂任何节点"""
	
	async def on_load(self) -> None:
		pass
	
	async def on_close(self) -> None:
		pass
