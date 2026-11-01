from pydantic	import BaseModel, Field

from ...protocols	import BaseRule

from typing	import List, Literal


class AnyKeywordsRule(BaseModel, BaseRule):
	
	mode	: Literal["any_keywords"]	= Field(default="any_keywords")
	words	: List[str]					= Field(default_factory=list, min_length=1, description="关键字列表")
	
	def is_hit(self, data: str) -> bool:
		"""任意一个命中就 True"""
		return any([word in data for word in self.words])
