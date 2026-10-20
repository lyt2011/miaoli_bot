from pydantic	import BaseModel, ConfigDict, Field, FilePath
from typing		import Annotated, List, Union

from .rules		import AnyKeywordsRule, MinKeywordsRule, RegexRule, SingleKeywordRule


Rule = Annotated[
	Union[AnyKeywordsRule, MinKeywordsRule, RegexRule, SingleKeywordRule],
	Field(discriminator="mode")
]


class Match(BaseModel):
	
	model_config = ConfigDict(extra="forbid")
	
	name	: str			= Field(..., description="")
	file	: FilePath		= Field(..., description="需要注入的提示词 (文件)")
	encoding: str			= Field(default="utf-8", description="编码格式")
	rules	: List[Rule]	= Field(default_factory=list, min_length=1, description="全部规则")
