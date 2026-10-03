from typing				import List, Union
from langgraph.types	import Send

from .base_action	import BaseAction, Delta

GotoTarget	= Union[str, Send, List[Union[str, Send]]]

class Goto(BaseAction):
	
	"""跳转到指定节点（事件） —— 携带已累积的增量"""
	
	def __init__(
		self, *,
		goto	: GotoTarget,
		updates	: Delta = None,
	) -> None:
		
		self.updates	= updates
		self.goto		= goto
