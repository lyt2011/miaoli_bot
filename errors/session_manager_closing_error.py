from .base_bot_error	import BaseBotError


class SessionManagerClosingError(BaseBotError):
	
	"""会话管理器正在关闭时调用了创建函数"""
	
	...