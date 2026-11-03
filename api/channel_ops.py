from ..core			import SHARE_STORE
from ..protocols	import BaseChannel
from ..consts		import CHANNEL_REGISTRY

from typing	import Callable


def register_channel(channel: BaseChannel) -> Callable[[], None]:
	
	"""幂等注册消息通道并返回幂等注销函数"""
	
	channel_registry = SHARE_STORE.recall(CHANNEL_REGISTRY)
	channel_registry.register(channel)
	
	def undo() -> None:
		channel_registry.unregister(channel)
	
	return undo