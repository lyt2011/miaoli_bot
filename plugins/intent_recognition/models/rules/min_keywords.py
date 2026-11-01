from pydantic	import BaseModel, Field

from ...protocols	import BaseRule

from typing	import List, Literal


class MinKeywordsRule(BaseModel, BaseRule):
	
	mode	: Literal["min_keywords"]	= Field(default="min_keywords")
	words	: List[str]					= Field(default_factory=list, min_length=1, description="关键字列表")
	count	: int						= Field(default=1, description="至少命中几个关键词才判 True")
	
	def is_hit(self, data: str) -> bool:
		"""批量计算命中数量并对比最低命中数"""
		return sum([word in data for word in self.words]) >= self.count
