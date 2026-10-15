from typing	import Protocol, Any, runtime_checkable


@runtime_checkable
class Parser(Protocol):
	
	"""
	解析器协议
	鸭子类型：任何实现了 is_accept / handle 的对象都能进解析链
	"""
	
	async def is_accept(self, data: Any) -> bool: ...
	async def handle(self, data: Any) -> Any: ...
