from pydantic	import BaseModel, Field

from ...protocols	import BaseRule

from typing	import Literal


class SingleKeywordRule(BaseModel, BaseRule):
	
	mode	: Literal["single_keyword"]	= Field(default="single_keyword")
	word	: str						= Field(..., description="关键字 单个")
	
	def is_hit(self, data: str) -> bool:
		"""单个命中就 True"""
		return self.word in data
