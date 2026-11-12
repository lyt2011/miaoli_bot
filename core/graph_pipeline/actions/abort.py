from ....protocols	import BaseNodeAction

from typing	import Optional

class Abort(BaseNodeAction):
	
	"""
	中止当前这一轮图运行
	管线会把它转成 AgentAborted 抛出 该异常继承 GraphBubbleUp
	因此不会被 _dispatch 的 except Exception 吞掉 而是冒到 ainvoke 调用处
	"""
	
	def __init__(
		self, *, 
		reason	: str				= "null",
		updates	: Optional[dict]	= None,
	) -> None:
		
		self.updates	= updates
		self.reason		= reason or "null"
