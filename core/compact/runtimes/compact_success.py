from langchain_core.messages	import BaseMessage

from typing			import List
from dataclasses	import dataclass


@dataclass(frozen=True)
class CompactSuccess:
	
	"""压缩结果"""
	
	summary		: str
	used_time	: float
	
	tokens_before	: int
	tokens_after	: int
	
	messages_before	: List[BaseMessage]
	messages_after	: List[BaseMessage]
