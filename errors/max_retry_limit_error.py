from .base_bot_error	import BaseBotError

from typing	import List


class MaxRetryLimitError(BaseBotError):
	
	"""重试次数到上限 或者遇到不可重试的错误"""
	
	def __init__(self, exceptions: List[Exception], times: int) -> None:
		
		self.exceptions	= exceptions
		self.times		= times
		
		super().__init__(f"LLM 调用失败 共尝试 {times} 次")
