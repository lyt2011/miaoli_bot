from langgraph.types	import Send

from ....protocols.node_action	import BaseNodeAction

from typing	import List, Optional, Union

GotoTarget	= Union[str, Send, List[Union[str, Send]]]

class Goto(BaseNodeAction):
	
	"""跳转到指定节点（事件） —— 携带已累积的增量"""
	
	def __init__(
		self, *,
		goto	: GotoTarget,
		updates	: Optional[dict] = None,
	) -> None:
		
		self.updates	= updates
		self.goto		= goto
