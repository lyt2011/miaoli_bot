from langchain_core.tools	import BaseTool

from .surface	import ToolSurface

from typing	import Dict


class ToolRegistry:
	
	"""
	工具注册器 内部用于工具的收集
	不提供给外部使用
	"""
	
	def __init__(self) -> None:
		self._tools: Dict[str, BaseTool] = {}
	
	def contains(self, tool: BaseTool) -> bool:
		"""获取 tool 是否已被添加"""
		return tool.name in self._tools
	
	def register(self, tool: BaseTool) -> None:
		"""幂等注册工具 直接替换"""
		self._tools.update({tool.name: tool})
	
	def unregister(self, tool: BaseTool) -> None:
		"""幂等注销工具 只注销自己注册的那一个"""
		if self._tools.get(tool.name) is tool:
			self._tools.pop(tool.name, None)
	
	def to_surface(self) -> ToolSurface:
		"""转为 ToolSurface"""
		return ToolSurface(self._tools)