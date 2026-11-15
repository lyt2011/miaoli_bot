from miaoli_bot.core	import PluginProtocol


class BaseLLM(PluginProtocol):
	
	"""模型接入层 提供 build_client 与带重试的 call_llm 不挂任何节点"""
	
	async def on_load(self) -> None:
		pass
	
	async def on_close(self) -> None:
		pass
