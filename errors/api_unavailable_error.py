from .base_bot_error	import BaseBotError


class APIUnavailableError(BaseBotError):
	
	"""api 不可用时抛出的报错 一般在工具里使用"""
	...