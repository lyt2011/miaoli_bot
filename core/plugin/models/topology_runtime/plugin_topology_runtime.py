from __future__	import annotations

from dataclasses	import dataclass, field
from typing			import TYPE_CHECKING, List, Optional, Self

from ..dependence	import Dependence

if TYPE_CHECKING:
	from ...plugin	import Plugin


@dataclass
class PluginTopologyRuntime:
	
	plugin		: Plugin
	dependences	: List[Dependence]

	index: Optional[int]	= field(default=None)
	
	@property
	def name(self) -> str:
		return self.plugin.package_name
	
	@classmethod
	def build(cls, plugin: Plugin) -> Self:
		return cls(plugin=plugin, dependences=list(plugin.metadata.dependences))
	
	def is_null_dependences(self) -> bool:
		"""是否为空依赖"""
		return not self.dependences
	
	def is_sorted(self) -> bool:
		"""是否已排序"""
		return self.index is not None
	
	def remove_dependence(self, name: str) -> None:
		"""通过名字移除依赖 (副本+原子替换)"""
		self.dependences = [dep for dep in self.dependences if dep.name != name]
	
	def mark_sorted(self, index: int) -> None:
		"""标注插件已排序"""
		self.index = index