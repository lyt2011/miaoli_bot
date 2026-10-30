from typing		import List, Self
from pydantic	import BaseModel, Field, model_validator

from ..errors	import RepeatDependenceError
from .dependence	import Dependence


class PluginMetadata(BaseModel):
	
	name		: str				= Field(..., description="插件名")
	entry_class	: str				= Field(..., description="入口类名", min_length=1)
	description	: str				= Field(default="", description="插件描述")
	dependences	: List[Dependence]	= Field(default_factory=list, description="插件依赖")
	
	
	@model_validator(mode="after")
	def repeat_dependence_checker(self) -> Self:
		
		"""检测重复依赖"""
		
		# 获取全部依赖 + 去重后的依赖
		all_dependences		= [dep.name for dep in self.dependences]
		deduped_dependences	= {dep.name for dep in self.dependences}
		
		# 过滤掉单个依赖 剩下的就是重复的依赖
		for deduped in deduped_dependences:
			all_dependences.remove(deduped)
		
		if all_dependences:
			raise RepeatDependenceError(f"插件 {self.name} 有重复依赖: {all_dependences}")
		
		return self