from ....protocols	import BaseNodeAction

from typing	import Optional


class Continue(BaseNodeAction):
	
	"""停止本事件剩余的处理器 —— 已累积的增量照常返回"""
	
	def __init__(self, *, updates: Optional[dict] = None) -> None:
		self.updates = updates
