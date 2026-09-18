from .base_bot_error	import BaseBotError


class MissFactoryError(BaseBotError):
	
	"""
	ensure_session 未命中缓存 且调用方没有传入建连工厂
	此时无法凭空建出 PiClient 只能报错
	"""
	...