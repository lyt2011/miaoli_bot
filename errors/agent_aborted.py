from langgraph.errors	import GraphBubbleUp

class AgentAborted(GraphBubbleUp):
	
	"""主动中止当前这一轮图运行"""
	
	def __init__(self, reason: str = "") -> None:
		
		self.reason = reason
		super().__init__(reason)
