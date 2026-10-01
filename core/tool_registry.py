from typing					import Dict, List
from langchain_core.tools	import BaseTool


class ToolRegistry:
	
	"""纯收益封装 便捷的注册"""
	
	def __init__(self) -> None:
		self._tools: Dict[str, BaseTool] = {}
	
	@property
	def tools(self) -> List[BaseTool]:
		return list(self._tools.values())
	
	def register(self, tool: BaseTool) -> None:
		self._tools[tool.name] = tool

	def remove(self, name: str, ignore_error: bool = False) -> None:
		
		if name not in self._tools and not ignore_error:
			raise KeyError(f"没有叫做 {name} 的工具")
		
		self._tools.pop(name)