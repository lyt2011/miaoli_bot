from typing	import Any, List, Protocol, runtime_checkable


@runtime_checkable
class ToolObtainanle(Protocol):
	"""可异步获取工具的"""
	async def get_tools(self) -> List[Any]: ...
