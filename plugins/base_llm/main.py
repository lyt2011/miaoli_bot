from miaoli_bot.core	import PluginProtocol


class BaseLLM(PluginProtocol):
	
	"""带重试的模型调用入口 只提供调用逻辑不挂任何节点"""
	
	async def on_load(self) -> None:
		pass
	
	async def on_close(self) -> None:
		pass
