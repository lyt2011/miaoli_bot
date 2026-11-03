from langgraph.errors	import GraphBubbleUp

class AgentAborted(GraphBubbleUp):
	
	"""
	主动中止当前这一轮图运行
	
	继承 GraphBubbleUp 因此不会被管线内层的 except Exception 吞掉
	而是冒泡到 ainvoke 调用处，由调用方决定怎么处理
	"""
	
	def __init__(self, reason: str = "") -> None:
		
		self.reason = reason
		super().__init__(reason)
