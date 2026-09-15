from .base_bot_error	import BaseBotError


class PIPromptBusyError(BaseBotError):
	
	"""
	pi 进程正在流式输出
	且 prompt 未定义 streamingBehavior 参数
	"""
	...