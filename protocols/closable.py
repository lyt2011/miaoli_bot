from typing	import Protocol, runtime_checkable


@runtime_checkable
class Closable(Protocol):
	
	"""
	可关闭资源的结构化约定
	runtime_checkable 只按属性名判定 不校验签名与幂等性
	"""
	
	async def close(self) -> None: ...