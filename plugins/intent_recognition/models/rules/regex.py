import re

from pydantic		import BaseModel, Field, PrivateAttr
from typing			import Literal, Optional

from ...protocols	import BaseRule


RegexCache = Optional[re.Pattern]


class RegexRule(BaseModel, BaseRule):
	
	mode	: Literal["regex"]	= Field(default="regex")
	regex	: str				= Field(..., description="正则匹配字符串")
	_cache	: RegexCache		= PrivateAttr(default=None)
	
	def is_hit(self, data: str) -> bool:
		
		"""re.search + 懒加载编译缓存"""
		
		if self._cache is None:
			self._cache = re.compile(self.regex)
		
		return bool(re.search(self._cache, data))
