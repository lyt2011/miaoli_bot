from dataclasses	import dataclass
from typing			import Any, Awaitable, Callable

@dataclass
class Handler:
	
	"""一个已注册的事件处理器：优先级 + 可调用对象"""
	
	event	: str
	priority: int
	function: Callable[..., Awaitable[Any]]
