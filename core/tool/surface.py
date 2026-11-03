from langchain_core.tools	import BaseTool

from typing	import Dict, List


class ToolSurface:
	
	"""
	工具表面层 提供给外部使用的实例 基于 Dict[tool.name, tool] 存储工具
	操作内部数据不会导致 ToolRegistry 损坏；说白了就是 ToolRegistry 的副本
	"""
	
	def __init__(self, tools_mapping: Dict[str, BaseTool]) -> None:
		self.tools_mapping = dict(tools_mapping)
	
	@property
	def tools(self) -> List[BaseTool]:
		"""返回按 tool.name 排序的工具列表副本"""
		return sorted(self.tools_mapping.values(), key=lambda tool: tool.name)
	
	def contains(self, tool: BaseTool) -> bool:
		"""获取 tool 是否已被添加"""
		return tool.name in self.tools_mapping
	
	def add(self, tool: BaseTool) -> None:
		"""幂等添加工具 相同工具替换后顺序不变"""
		self.tools_mapping.update({tool.name: tool})
	
	def delete(self, tool: BaseTool) -> None:
		"""幂等删除工具 只删除自己持有的那一个"""
		if self.tools_mapping.get(tool.name) is tool:
			self.tools_mapping.pop(tool.name, None)