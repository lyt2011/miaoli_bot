from .base_action	import BaseAction, Delta

class Continue(BaseAction):
	
	"""停止本事件剩余的处理器 —— 已累积的增量照常返回"""
	
	def __init__(self, *, updates: Delta = None) -> None:
		self.updates = updates
