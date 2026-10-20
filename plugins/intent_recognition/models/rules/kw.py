from pydantic		import BaseModel, Field
from typing			import Literal

from ...protocols	import BaseRule


class KeywordRule(BaseModel, BaseRule):
	
	mode: Literal["keyword"]	= Field(default="keyword")
	word: str					= Field(..., description="关键词 单个")
	
	def is_hit(self, data: str) -> bool:
		"""单个命中就 True"""
		return self.word in data
